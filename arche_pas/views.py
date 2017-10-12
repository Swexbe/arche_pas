import deform
from arche.events import ObjectUpdatedEvent
from arche.interfaces import IUser
from arche.security import PERM_EDIT
from arche.utils import get_content_schemas
from arche.views.base import BaseForm, BaseView
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPNotFound
from six import string_types
from zope.component.event import objectEventNotify
from zope.interface.interfaces import ComponentLookupError

from arche_pas import _
from arche_pas.interfaces import IPASProvider
from arche_pas.interfaces import IProviderData


class BeginAuthView(BaseView):

    def __call__(self):
        provider_name = self.request.matchdict.get('provider', '')
        provider = self.request.registry.queryAdapter(self.request, IPASProvider, name = provider_name)
        return HTTPFound(location=provider.begin())


class CallbackAuthView(BaseView):

    def __call__(self):
        #FIXME: Handle ALL provider exceptions here!
        provider_name = self.request.matchdict.get('provider', '')
        provider = self.request.registry.queryAdapter(self.request, IPASProvider, name = provider_name)
        #FIXME: Redirect when a user is logged in and ask about attaching accounts?
        #FIXME: Handle exceptions here
        profile_data = provider.callback()
        user_ident = profile_data.get(provider.id_key, None)
        if not user_ident:
            raise HTTPBadRequest("Profile response didn't contain a user identifier.")
        user = provider.get_user(user_ident)
        if user:
            print "CALLBACK LOGIN"
            self.flash_messages.add(_("Logged in via ${provider}",
                                      mapping={'provider': self.request.localizer.translate(provider.title)}),
                                    type='success')
            return provider.login(user)
        else:
            print "CALLBACK REGISTER"
            reg_response = provider.prepare_register(profile_data)
            if isinstance(reg_response, string_types):
                return HTTPFound(
                    location = self.request.route_url('pas_register',
                                                      provider = provider.name,
                                                      reg_id = reg_response)
                )
            else:
                return reg_response


class RegisterPASForm(BaseForm):
    type_name = u'Auth'
    schema_name = 'register_finish'
    title = _(u"Complete registration")

    def __init__(self, context, request):
        super(RegisterPASForm, self).__init__(context, request)
        if request.authenticated_userid != None:
            raise HTTPForbidden(_(u"Already logged in."))

    @property
    def buttons(self):
        return (deform.Button('register', title = _("Register"), css_class = 'btn btn-primary'),
                 self.button_cancel,)

    @property
    def provider(self):
        provider_name = self.request.matchdict.get('provider', '')
        try:
            return self.request.registry.getAdapter(self.request, IPASProvider, name = provider_name)
        except ComponentLookupError:
            raise HTTPNotFound("No provider named %s" % provider_name)

    @property
    def reg_id(self):
        return self.request.matchdict.get('reg_id', '')

    @property
    def provider_response(self):
        data = self.request.session.get(self.reg_id, None)
        if not data:
            raise HTTPBadRequest("No session data found from provider")
        return data

    def appstruct(self):
        return self.provider.registration_appstruct(self.provider_response)

    def get_schema(self):
        schema = get_content_schemas(self.request.registry)[self.type_name][self.schema_name]()
        for k in ('email', 'password'):
            if k in schema:
                del schema[k]
        return schema

    def register_success(self, appstruct):
        factory = self.request.content_factories['User']
        userid = appstruct.pop('userid')
        redirect_url = appstruct.pop('came_from', None)
        email = self.provider.get_email(self.provider_response)
        #FIXME: Flag for validated email
        user = factory(email = email, **appstruct)
        self.context['users'][userid] = user
        self.provider.store(user, self.provider_response)
        self.flash_messages.add(_("Welcome, you're now registered!"), type="success")
        self.request.session.pop(self.reg_id, None)
        return self.provider.login(user, first_login = True, came_from = redirect_url)


class ConfirmLinkAccountPASForm(BaseForm):
    type_name = 'PAS'
    schema_name = 'link_data'
    title = _("Link account?")

    @property
    def buttons(self):
        return (deform.Button('link', title = _("Link account"),), #css_class = 'btn btn-success'
                self.button_cancel,)

    def __init__(self, context, request):
        super(ConfirmLinkAccountPASForm, self).__init__(context, request)
        if not request.authenticated_userid:
            raise HTTPForbidden(_("You need to be logged in to link an account"))
        self.provider_response #To provoke test

    @property
    def provider(self):
        provider_name = self.request.matchdict.get('provider', '')
        try:
            return self.request.registry.getAdapter(self.request, IPASProvider, name = provider_name)
        except ComponentLookupError:
            raise HTTPNotFound("No provider named %s" % provider_name)

    @property
    def reg_id(self):
        return self.request.matchdict.get('reg_id', '')

    @property
    def provider_response(self):
        data = self.request.session.get(self.reg_id, None)
        if not data:
            raise HTTPBadRequest("No session data found from provider. You may need to restart the procedure.")
        return data

    def link_success(self, appstruct):
        self.provider.store(self.request.profile, self.provider_response)
    #     #FIXME: Flag for validated email
        #FIXME: Decide about overwrite of email
        provider_title = self.request.localizer.translate(self.provider.title)
        self.flash_messages.add(_("You may now login with ${provider_title}.",
                                  mapping={'provider_title': provider_title}),
                                type="success")
        self.request.session.pop(self.reg_id, None)
        return HTTPFound(location=self.request.resource_url(self.context))


class RemovePASDataForm(BaseForm):
    type_name = 'PAS'
    schema_name = 'remove_data'

    @property
    def buttons(self):
        return (deform.Button('remove', title = _("Remove"), css_class = 'btn btn-danger'),
                 self.button_cancel,)

    def remove_success(self, appstruct):
        if appstruct.get('remove_password', False) == True:
            self.context.password = None
        if appstruct['providers_to_remove']:
            provider_data = IProviderData(self.context)
            for provider_name in appstruct['providers_to_remove']:
                del provider_data[provider_name]
            event = ObjectUpdatedEvent(self.context, changed = ['pas_ident'])
            objectEventNotify(event)
            self.flash_messages.add(_("Removed successfully"), type='success')
        return HTTPFound(location=self.request.resource_url(self.context))


def includeme(config):
    config.add_route('pas_begin', '/pas_begin/{provider}')
    config.add_view(BeginAuthView, route_name='pas_begin')
    config.add_route('pas_callback', '/pas_callback/{provider}')
    config.add_view(CallbackAuthView, route_name='pas_callback')
    config.add_route('pas_register', '/pas_register/{provider}/{reg_id}')
    config.add_view(RegisterPASForm, route_name='pas_register',
                    renderer='arche:templates/form.pt')
    config.add_view(RemovePASDataForm, context=IUser, name='remove_pas',
                    renderer='arche:templates/form.pt', permission=PERM_EDIT)
    config.add_route('pas_link', '/pas_link/{provider}/{reg_id}')
    config.add_view(ConfirmLinkAccountPASForm, route_name='pas_link',
                    renderer='arche:templates/form.pt')
