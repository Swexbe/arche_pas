# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from uuid import uuid4

from BTrees.OOBTree import OOBTree
from UserDict import IterableUserDict
from arche.events import ObjectUpdatedEvent
from arche.events import WillLoginEvent
from arche.interfaces import IFlashMessages
from arche.interfaces import IRoot
from arche.interfaces import IUser
from pyramid.httpexceptions import HTTPFound, HTTPForbidden
from pyramid.security import remember
from zope.component import adapter
from zope.component.event import objectEventNotify
from zope.interface import implementer

from arche_pas import _
from arche_pas.exceptions import ProviderConfigError
from arche_pas.interfaces import IProviderData
from arche_pas.interfaces import IPASProvider


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


#@implementer(IPASProviderFactory)
#class PASProviderFactory(object):

#Skriv så det är objektet som registreras som adapter och sedan ropas på istället vid adaptering

@implementer(IPASProvider)
@adapter(IRoot)
class PASProvider(object):
    name = ''
    title = ''
    id_key = ''
    settings = None
    default_settings = {}
    paster_config_ns = ''
    ProviderConfigError = ProviderConfigError

    def __init__(self, context):
        self.context = context

    @classmethod
    def update_settings(cls, dictobj=None, **kw):
        if cls.settings is None:
            cls.settings = cls.default_settings.copy()
        if dictobj:
            cls.settings.update(dictobj)
        if kw:
            cls.settings.update(kw)

    @classmethod
    def validate_settings(cls): #pragma: no coverage
        pass

    def begin(self, request):
        return ""

    def callback(self, request):
        return {}

    def callback_url(self, request):
        """ Same as redirect_uri for some providers """
        return request.route_url('pas_callback', provider=self.name)

    def get_id(self, user):
        provider_data = IProviderData(user)
        return provider_data.get(self.name, {}).get(self.id_key, None)

    def get_user(self, request, user_ident):
        query = "pas_ident == %s and type_name == 'User'" % str((self.name, user_ident))
        docids = self.context.catalog.query(query)[1]
        for obj in request.resolve_docids(docids, perm = None):
            if IUser.providedBy(obj):
                return obj

    def prepare_register(self, request, data):
        #Figure out if a user with that email validated already exists
        validated_email = self.get_validated_email(data)
        #FIXME: Handle cases where email ISN'T validated
        user = self.context['users'].get_user_by_email(validated_email, only_validated=False)
        if user:
            if user.email_validated == False:
                msg = _("user_found_without_validated_address",
                        default = "A user account was found with this address, "
                                  "but the address hasn't been validated. "
                                  "If this is your account - login first and "
                                  "then tie this login provider to your account.")
                raise HTTPForbidden(msg)
            self.store(user, data)
            fm = IFlashMessages(request)
            msg = _("data_tied_at_login",
                    default="Since you already had an account with the same email address validated, "
                            "you've been logged in as that user. Your accounts have also been linked.")
            fm.add(msg, type="success", auto_destruct=False)
            #Will return a HTTP 302
            return self.login(user, request)
        #Register
        reg_id = str(uuid4())
        #Hash data to provide checksum?
        request.session[reg_id] = data
        #Register this user
        return reg_id

    def login(self, user, request, first_login = False, came_from = None):
        event = WillLoginEvent(user, request = request, first_login = first_login)
        request.registry.notify(event)
        headers = remember(request, user.userid)
        url = came_from and came_from or request.resource_url(self.context)
        return HTTPFound(url, headers = headers)

    def store(self, user, data):
        assert IUser.providedBy(user)
        assert isinstance(data, dict)
        provider_data = IProviderData(user)
        provider_data[self.name] = data
        event = ObjectUpdatedEvent(user, changed = ['pas_ident'])
        objectEventNotify(event)

    def get_validated_email(self, response): #pragma: no coverage
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


def includeme(config):
    config.registry.registerAdapter(ProviderData)
    config.add_directive('add_pas', add_pas)
