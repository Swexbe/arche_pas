from arche.events import ObjectUpdatedEvent
from arche.interfaces import IUser
from arche.security import NO_PERMISSION_REQUIRED, PERM_EDIT
from arche.utils import get_content_schemas
from arche.views.base import BaseForm, BaseView
from arche_pas.interfaces import IPASProvider, IProviderData
from pyramid.httpexceptions import HTTPForbidden, HTTPBadRequest, HTTPNotFound
from pyramid.httpexceptions import HTTPFound
from pyramid.security import remember
import deform

from arche_pas import  _
#from arche_pas.exceptions import UserNotFoundError
#from arche_pas.interfaces import IPluggableAuth
#from arche_pas.models import get_auth_info
from six import string_types
from zope.component.event import objectEventNotify
from zope.interface.interfaces import ComponentLookupError


def includeme(config):
    config.add_route('pas_begin', '/pas_begin/{provider}')
    config.add_view(BeginAuthView, route_name = 'pas_begin')
    config.add_route('pas_callback', '/pas_callback/{provider}')
    config.add_view(CallbackAuthView, route_name = 'pas_callback')
    config.add_route('pas_register', '/pas_register/{provider}/{reg_id}')
    config.add_view(RegisterPASForm, route_name = 'pas_register', renderer='arche:templates/form.pt')
    config.add_view(RemovePASDataForm, context=IUser, name='remove_pas', renderer='arche:templates/form.pt', permission=PERM_EDIT)
    # config.add_view(logged_in,
    #                 route_name = 'pas_logged_in')
    # config.add_route('pas_logged_in', '/__pas_logged_in__')
    # config.add_view(RegisterPASView,
    #                 route_name = 'pas_register',
    #                 renderer = "arche:templates/form.pt")
    # config.add_route('pas_register', '/__pas_register__/{provider_name}')
    # #FIXME: Add any other  generic badness...
    # config.add_view(exception_view, context = 'openid.yadis.discover.DiscoveryFailure', permission = NO_PERMISSION_REQUIRED)
    # config.add_view(exception_view, context = 'velruse.exceptions.VelruseException', permission = NO_PERMISSION_REQUIRED)


class BeginAuthView(BaseView):

    def __call__(self):
        provider_name = self.request.matchdict.get('provider', '')
        provider = self.request.registry.queryAdapter(self.context, IPASProvider, name = provider_name)
        return HTTPFound(location=provider.begin(self.request))


class CallbackAuthView(BaseView):

    def __call__(self):
        #FIXME: Handle ALL provider exceptions here!
        provider_name = self.request.matchdict.get('provider', '')
        provider = self.request.registry.queryAdapter(self.context, IPASProvider, name = provider_name)
        #FIXME: Redirect when a user is logged in and ask about attaching accounts?
        profile_data = provider.callback(self.request)
        user_ident = profile_data.get(provider.id_key, None)
        if not user_ident:
            raise HTTPBadRequest("Profile response didn't contain a user identifier.")
        user = provider.get_user(self.request, user_ident)
        if user:
            print "CALLBACK LOGIN"
            self.flash_messages.add(_("Logged in via ${provider}",
                                      mapping={'provider': self.request.localizer.translate(provider.title)}),
                                    type='success')
            return provider.login(user, self.request)
        else:
            print "CALLBACK REGISTER"
            reg_response = provider.prepare_register(self.request, profile_data)
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
            return self.request.registry.getAdapter(self.context, IPASProvider, name = provider_name)
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
        email = self.provider.get_validated_email(self.provider_response)
        if not email:
            raise HTTPBadRequest("No validated email from provider")
        user = factory(email = email, **appstruct)
        self.context['users'][userid] = user
        self.provider.store(user, self.provider_response)
        self.flash_messages.add(_("Welcome, you're now registered!"), type="success")
        self.request.session.pop(self.reg_id, None)
        return self.provider.login(user, self.request, first_login = True, came_from = redirect_url)


class RemovePASDataForm(BaseForm):
    type_name = u'PAS'
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

# def _try_to_add_error(request, msg):
#     fm = request.registry.queryAdapter(request, IFlashMessages)
#     if fm:
#         msg = _(u"third_party_login_error",
#                  default="A third party request caused an error: '${msg}'",
#                  mapping={'msg': msg})
#         fm.add(msg, type = 'error')
#
# def exception_view(context, request):
#     _try_to_add_error(request, context.message)
#     return HTTPFound(location = "/")
#
# def logged_in(context, request):
#     """ Handle login through another service. Note that this is not the same as a local login.
#         A cookie still needs to be set. Also, it's possible to run this method for a user that's
#         already logged in locally, ie wanting to connect to a another service to use it as auth.
#     """
#     userid = request.authenticated_userid
#     auth_info = get_auth_info(request)
#     if not auth_info:
#         raise HTTPForbidden("No auth session in progress")
#     if 'error' in auth_info:
#         _try_to_add_error(request, auth_info['error'])
#         return HTTPFound(location = "/")
#     auth_method = request.registry.queryMultiAdapter((context, request),
#                                                      IPluggableAuth,
#                                                      name = auth_info['provider_type'])
#     if not auth_method:
#         raise HTTPForbidden("There's no login provider called '%s'" % auth_info['provider_type'])
#     if not userid:
#         appstruct = auth_method.appstruct(auth_info)
#         try:
#             return auth_method.login(appstruct)
#         except UserNotFoundError:
#             #May need to register?
#             url = auth_method.registration_url(token = request.params['token'])
#             return HTTPFound(location = url)
#     else:
#         user = context['users'][userid]
#         auth_method.set_auth_domain(user, auth_info['provider_type'])
#         url = request.resource_url(context)
#         return HTTPFound(location = url)
