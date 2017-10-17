# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from UserDict import IterableUserDict

from BTrees.OOBTree import OOBTree
from arche.events import ObjectUpdatedEvent
from arche.events import WillLoginEvent
from arche.interfaces import IUser
from pyramid.httpexceptions import HTTPFound
from pyramid.interfaces import IRequest
from pyramid.security import remember
from pyramid.threadlocal import get_current_registry
from six import string_types
from zope.component import adapter
from zope.component.event import objectEventNotify
from zope.interface import implementer

from arche_pas import logger
from arche_pas.exceptions import ProviderConfigError
from arche_pas.exceptions import RegistrationCaseMissmatch
from arche_pas.interfaces import IPASProvider
from arche_pas.interfaces import IProviderData
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
    image_key = ''
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
        if self.image_key:
            return response.get(self.image_key, None)

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


def register_case(registry, name, **kw):
    """ Construct a registration case from params """
    #FIXME: Make sure no conflicting params are present
    util = RegistrationCase(name, **kw)
    for (name, rutil) in registry.getUtilitiesFor(IRegistrationCase):
        util.cmp_crit(rutil)
    registry.registerUtility(util, name=util.name)


def includeme(config):
    config.registry.registerAdapter(ProviderData)
    config.add_directive('add_pas', add_pas)
