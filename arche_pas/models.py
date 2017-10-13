# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from uuid import uuid4

from BTrees.OOBTree import OOBTree
from UserDict import IterableUserDict
from arche.events import ObjectUpdatedEvent
from arche.events import WillLoginEvent
from arche.interfaces import IFlashMessages
from arche.interfaces import IUser
from pyramid.httpexceptions import HTTPFound
from pyramid.interfaces import IRequest
from pyramid.security import remember
from pyramid.threadlocal import get_current_registry
from six import string_types
from zope.component import adapter
from zope.component.event import objectEventNotify
from zope.interface import implementer

from arche_pas import _
from arche_pas import logger
from arche_pas.exceptions import ProviderConfigError
from arche_pas.exceptions import RegistrationCaseMissmatch
from arche_pas.interfaces import IProviderData
from arche_pas.interfaces import IPASProvider
from arche_pas.interfaces import IRegistrationCase


@implementer(IProviderData)
@adapter(IUser)
class ProviderData(IterableUserDict):

    def __init__(self, context):
        self.context = context

    @property
    def data(self):
        try:
            return self.context.__pas_provider_data__
        except AttributeError:
            self.context.__pas_provider_data__ = OOBTree()
            return self.context.__pas_provider_data__

    def __setitem__(self, key, item):
        self.data[key] = OOBTree(item)

    def __repr__(self): #pragma: no coverage
        klass = self.__class__
        classname = '%s.%s' % (klass.__module__, klass.__name__)
        return '<%s adapting %s containing %s items>' % (classname,
                                                   self.context,
                                                   len(self))


@implementer(IRegistrationCase)
class RegistrationCase(object):
    """
        Behaviour of conditions:
        True/False, must be that value specifically
        None, skipped
    """
    require_authenticated = None #User must be logged in
    email_validated_provider = None #The provider says that the email is validated
    email_validated_locally = None #Locally validated
    user_exist_locally = None #User exists
    email_from_provider = None #Any kind of email from provider
    provider_validation_trusted = None #The providers email validation is trusted
    title = ""
    name = ""

    def __init__(self, name, title = "", callback=None, **kw):
        self.name = name
        self.title = title and title or name
        assert callable(callback), "No callback attached"
        self.callback = callback
        for (k, v) in kw.items():
            if hasattr(self, k):
                setattr(self, k, v)
            else:
                raise AttributeError("No such attribute %s" % k)

    def as_dict(self):
        keys = ('require_authenticated', 'email_validated_provider',
                'email_validated_locally', 'user_exist_locally',
                'email_from_provider', 'provider_validation_trusted')
        data = {}
        for k in keys:
            data[k] = getattr(self, k, None)
        return data

    def cmp_crit(self, other):
        if isinstance(other, RegistrationCase):
            if self.as_dict() == other.as_dict():
                raise ValueError("Duplicate criteria between %s and %s" % (self.name, other.name))
        else:
            raise TypeError("Must be another RegistrationCase instance")

    def match(self, params):
        """ Calc match score for case. Return a list with all matched as 2, all none as 1.
            Raise exception if something didn't match.
        """
        assert isinstance(params, dict), "params must be a dict"
        scores = []
        for (k, v) in params.items():
            val = getattr(self, k)
            if val is None or v is None:
                scores.append(1)
            elif val == v:
                scores.append(2)
            else:
                raise RegistrationCaseMissmatch("%s != %s" % (val , v))
        return scores


@implementer(IPASProvider)
@adapter(IRequest)
class PASProvider(object):
    name = ''
    title = ''
    id_key = ''
    settings = None
    default_settings = {}
    paster_config_ns = ''
    trust_email = False
    ProviderConfigError = ProviderConfigError
    logger = logger

    def __init__(self, request):
        self.request = request

    @classmethod
    def update_settings(cls, dictobj=None, **kw):
        if cls.settings is None:
            cls.settings = cls.default_settings.copy()
        if dictobj:
            cls.settings.update(dictobj)
        if kw:
            cls.settings.update(kw)
        #Update own attributes from the 'provider' key
        provider_settings = cls.settings.pop('provider', {})
        for (k, v) in provider_settings.items():
            if hasattr(cls, k):
                setattr(cls, k ,v)
            else:
                raise cls.ProviderConfigError("%s has no attribute %s" % (cls, k))

    @classmethod
    def validate_settings(cls): #pragma: no coverage
        try:
            assert isinstance(cls.settings, dict), \
                "No configuration found for provider %r" % cls.name
            for str_k in ('client_id', 'auth_uri', 'token_uri', 'client_secret'):
                assert isinstance(cls.settings.get(str_k, None), string_types), \
                    "Missing config key %r for provider %r" % (str_k, cls.name)
        except AssertionError as exc:
            raise cls.ProviderConfigError(exc.message)

    def begin(self):
        return ""

    def callback(self):
        return {}

    def callback_url(self):
        """ Same as redirect_uri for some providers """
        return self.request.route_url('pas_callback', provider=self.name)

    def get_id(self, user):
        provider_data = IProviderData(user)
        return provider_data.get(self.name, {}).get(self.id_key, None)

    def get_user(self, user_ident):
        query = "pas_ident == %s and type_name == 'User'" % str((self.name, user_ident))
        docids = self.request.root.catalog.query(query)[1]
        for obj in self.request.resolve_docids(docids, perm = None):
            if IUser.providedBy(obj):
                return obj

    def build_reg_case_params(self, data):
        """ Get the result params to map a reg case against """
        validated_email = self.get_email(data, validated=True)
        email = self.get_email(data)
        query_email = validated_email and validated_email or email
        if query_email:
            user = self.request.root['users'].get_user_by_email(query_email, only_validated=False)
        else:
            user = None
        params = dict(
            require_authenticated = bool(self.request.authenticated_userid),
            email_validated_provider = bool(validated_email),
            email_validated_locally = user and user.email_validated or False,
            user_exist_locally = user and True or False,
            email_from_provider = bool(query_email),
            provider_validation_trusted = self.trust_email,
        )
        #Handle quirks
        if not params['provider_validation_trusted']:
            del params['email_validated_provider']
        return params

    def prepare_register(self, data):
        """
        :param data:
        :return: reg_id or non-error HTTPException (usually redirect)
        """
        self.logger.debug("prepare_register called with data %s", data)
        reg_case_params = self.build_reg_case_params(data)
        reg_case = get_register_case(registry=self.request.registry, **reg_case_params)
        self.logger.debug("Got registration case util: %s", reg_case.name)
        #Really returned?
        email = self.get_email(data)
        if email:
            user = self.request.root['users'].get_user_by_email(email, only_validated=False)
        else:
            user = None
        return reg_case.callback(self, user, data)

    def login(self, user, first_login = False, came_from = None):
        event = WillLoginEvent(user, request = self.request, first_login = first_login)
        self.request.registry.notify(event)
        headers = remember(self.request, user.userid)
        url = came_from and came_from or self.request.resource_url(self.request.root)
        return HTTPFound(url, headers = headers)

    def store(self, user, data):
        assert IUser.providedBy(user)
        assert isinstance(data, dict)
        provider_data = IProviderData(user)
        provider_data[self.name] = data
        event = ObjectUpdatedEvent(user, changed = ['pas_ident'])
        objectEventNotify(event)

    def get_email(self, response, validated=False): #pragma: no coverage
        pass

    def get_profile_image(self, response):
        pass

    def registration_appstruct(self, response): #pragma: no coverage
        return {}


def add_pas(config, factory):
    """
    :param config: Instance of a Pyramid configuration object.
    :param factory: The PasProvider factory.
    """
    from os.path import isfile
    from json import loads
    assert IPASProvider.implementedBy(factory)
    assert factory.name, "Factory must have a name"
    assert factory.paster_config_ns, "Factory must have a paster_config_ns set"
    filename = config.registry.settings.get(factory.paster_config_ns, None)
    if not isfile(filename):
        raise IOError("Can't find any file at: '%s'" % filename)
    with open(filename, 'r') as f:
        config_data = f.read()
    pas_settings = loads(config_data)
    factory.update_settings(pas_settings)
    factory.validate_settings()
    config.registry.registerAdapter(factory, name = factory.name)


def callback_case_1(provider, user, data):
    provider.store(user, data)
    fm = IFlashMessages(provider.request)
    msg = _("data_tied_at_login",
            default="Since you already had an account with the same email address validated, "
                    "you've been logged in as that user. Your accounts have also been linked.")
    fm.add(msg, type="success", auto_destruct=False)
    # Will return a HTTP 302
    return provider.login(user)


def callback_case_2(provider, user, data):
    user.email_validated = True
    provider.store(user, data)
    fm = IFlashMessages(provider.request)
    msg = _("accounts_linked_verified_since_logged_in",
            default="You've linked your external login to this account.")
    fm.add(msg, type="success", auto_destruct=False)
    # Will return a HTTP 302
    return provider.login(user)


def callback_must_be_logged_in(provider, user, data):
    email = provider.get_email(data, validated=False)
    msg = _("user_email_present",
            default="There's already a user registered here with your email address: '${email}' "
                    "If this is your account, please login here first to "
                    "connect the two accounts.",
            mapping={'email': email})
    fm = IFlashMessages(provider.request)
    fm.add(msg, type='danger', auto_destruct=False, require_commit=False)
    raise HTTPFound(location=provider.request.resource_url(provider.request.root, 'login'))


def callback_register(provider, user, data):
    reg_id = str(uuid4())
    provider.request.session[reg_id] = data
    # Register this user
    return reg_id


def callback_maybe_attach_account(provider, user, data):
    """ Only for logged in users."""
    reg_id = str(uuid4())
    provider.request.session[reg_id] = data
    raise HTTPFound(location=provider.request.route_url('pas_link', provider=provider.name, reg_id=reg_id))


def register_case(registry, name, **kw):
    """ Construct a registration case from params """
    #FIXME: Make sure no conflicting params are present
    util = RegistrationCase(name, **kw)
    for (name, rutil) in registry.getUtilitiesFor(IRegistrationCase):
        util.cmp_crit(rutil)
    registry.registerUtility(util, name=util.name)


def get_register_case(registry=None, as_scores = False, **kw):
    """ Get the best mapped register case. """
    if registry is None:
        registry = get_current_registry()
    score = {}
    for (name, util) in registry.getUtilitiesFor(IRegistrationCase):
        try:
            score[name] = util.match(kw)
        except RegistrationCaseMissmatch:
            score[name] = []
    if as_scores:
        return score
    #Find the most specific one - most matches first
    longest = 0
    highest_sum = 0
    for v in score.values():
        if len(v) > longest:
            longest = len(v)
    current_best = None
    for k in tuple(score.keys()):
        if len(score[k]) < longest:
            del score[k]
            continue
        if sum(score[k]) > highest_sum:
            highest_sum = sum(score[k])
            if current_best:
                del score[current_best]
            current_best = k
    #At this point, only one should remain otherwise something has gone wrong
    if highest_sum == 0:
        raise ValueError("Nothing matched, params was: %s" % kw)
    if len(score) != 1:
        raise ValueError("More than 1 registration method matched. Values: '%s'" % "', '".join(score.keys()))
    return registry.getUtility(IRegistrationCase, name=current_best)


def includeme(config):
    """
    Different registration cases for email:
    1) Validated on server, validated locally and exist
    2) Validated on server, exists locally but not validated, user logged in
    3) Validated on server, exists locally but not validated, user not logged in
    4) Validated on server, doesn't exist locally
    4A) Validated on server, doesn't match locally but user logged in
     - change email?

    Serious security breach risk:
    5) Not validated/trusted on server, validated locally, user logged in
       - Serious risk of hack: cross site scripting or accidental attach of credentials
    6) Not validated/trusted on server, validated locally, user not logged in

    7) Not validated/trusted on server, exists locally but not validated, user logged in
    7A) Not validated/trusted on server, local user not matched, user logged in
    8) Not validated/trusted on server, exists locally but not validated, user not logged in
    9) Not validated/trusted on server, doesn't exist locally, not logged in

    10) No email from provider, user logged in
    11) No email from provider, user not logged in
    """
    config.registry.registerAdapter(ProviderData)
    config.add_directive('add_pas', add_pas)

    register_case(
        config.registry,
        'case1',
        title = "Validated on server, validated locally and user exists",
        require_authenticated = None,
        email_validated_provider = True,
        email_validated_locally = True,
        user_exist_locally = True,
        provider_validation_trusted = True,
        callback=callback_case_1,
    )
    register_case(
        config.registry,
        'case2',
        title = "Validated on server, exists locally but not validated, user logged in",
        require_authenticated = True,
        email_validated_provider = True,
        email_validated_locally = False,
        user_exist_locally = True,
        provider_validation_trusted = True,
        callback = callback_case_2,
    )
    register_case(
        config.registry,
        'case3',
        title = "Validated on server, exists locally but not validated, user not logged in",
        require_authenticated = False,
        email_validated_provider = True,
        email_validated_locally = False,
        user_exist_locally = True,
        provider_validation_trusted = True,
        callback = callback_must_be_logged_in,
    )
    register_case(
        config.registry,
        'case4',
        title = "Validated on server, doesn't exist locally",
        require_authenticated = False,
        email_validated_provider = True,
        #email_validated_locally = False,
        user_exist_locally = False,
        provider_validation_trusted = True,
        callback = callback_register,
    )
    register_case(
        config.registry,
        'case4a',
        title = "Validated on server, doesn't match locally but is authenticated",
        require_authenticated = True,
        email_validated_provider = True,
        #email_validated_locally = False,
        user_exist_locally = False,
        provider_validation_trusted = True,
        callback = callback_maybe_attach_account,
    )
    register_case(
        config.registry,
        'case5',
        title="Not validated/trusted on server, validated locally, user logged in",
        require_authenticated = True,
        #email_validated_provider = None,
        email_validated_locally = True,
        #user_exist_locally = True, Should be caught by email_validated_locally?
        email_from_provider = None,
        provider_validation_trusted = False,
        callback = callback_maybe_attach_account,
    )
    register_case(
        config.registry,
        'case6',
        title="Not validated/trusted on server, validated locally, user not logged in",
        require_authenticated = False,
        #email_validated_provider = None,
        email_validated_locally = True,
        #user_exist_locally = True, Should be caught by email_validated_locally?
        email_from_provider = None,
        provider_validation_trusted = False,
        callback = callback_must_be_logged_in,
    )
    register_case(
        config.registry,
        'case7',
        title="Not validated/trusted on server, exists locally but not validated, user logged in",
        require_authenticated = True,
        email_validated_provider = None,
        email_validated_locally = False,
        user_exist_locally = True,
        email_from_provider = True,
        provider_validation_trusted = False,
        callback = callback_maybe_attach_account,
    )
    register_case(
        config.registry,
        'case7a',
        title="Not validated/trusted on server, local user not matched, user logged in",
        require_authenticated = True,
        email_validated_provider = None,
        email_validated_locally = False,
        user_exist_locally = False,
        email_from_provider = True,
        provider_validation_trusted = False,
        callback = callback_maybe_attach_account, #FIXME: And change email?
    )
    register_case(
        config.registry,
        'case8',
        title="Not validated/trusted on server, exists locally but not validated, user not logged in",
        require_authenticated = False,
        email_validated_provider = None,
        email_validated_locally = False,
        user_exist_locally = True,
        email_from_provider = None,
        provider_validation_trusted = False,
        callback = callback_must_be_logged_in,
    )
    register_case(
        config.registry,
        'case9',
        title="Not validated/trusted on server, doesn't exist locally",
        require_authenticated = False,
        email_validated_provider = None,
        #email_validated_locally = False,
        user_exist_locally = False,
        email_from_provider = True,
        provider_validation_trusted = False,
        callback = callback_register,
    )
    register_case(
        config.registry,
        'case10',
        title="No email from provider, user logged in",
        require_authenticated = True,
        email_validated_provider = None,
        email_validated_locally = None,
       # user_exist_locally = True,
        email_from_provider = False,
        provider_validation_trusted = None,
        callback = callback_maybe_attach_account,
    )
    register_case(
        config.registry,
        'case11',
        title="No email from provider, user not logged in",
        require_authenticated = False,
        #email_validated_provider = None,
        #email_validated_locally = None,
        #user_exist_locally = None,
        email_from_provider = False,
        #provider_validation_trusted = None,
        callback=callback_register, #Allow registration here?
    )
