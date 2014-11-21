from arche.interfaces import IFlashMessages
from arche.security import NO_PERMISSION_REQUIRED
from arche.views.base import BaseForm
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPFound
from pyramid.security import remember
import deform

from arche_pas import  _
from arche_pas.exceptions import UserNotFoundError
from arche_pas.interfaces import IPluggableAuth
from arche_pas.models import get_auth_info


def includeme(config):
    config.add_view(logged_in,
                    route_name = 'pas_logged_in')
    config.add_route('pas_logged_in', '/__pas_logged_in__')
    config.add_view(RegisterPASView,
                    route_name = 'pas_register',
                    renderer = "arche:templates/form.pt")
    config.add_route('pas_register', '/__pas_register__/{provider_name}')
    #FIXME: Add any other  generic badness...
    config.add_view(exception_view, context = 'openid.yadis.discover.DiscoveryFailure', permission = NO_PERMISSION_REQUIRED)
    config.add_view(exception_view, context = 'velruse.exceptions.VelruseException', permission = NO_PERMISSION_REQUIRED)

def _try_to_add_error(request, msg):
    fm = request.registry.queryAdapter(request, IFlashMessages)
    if fm:
        msg = _(u"third_party_login_error",
                 default="A third party request caused an error: '${msg}'",
                 mapping={'msg': msg})
        fm.add(msg, type = 'error')

def exception_view(context, request):
    _try_to_add_error(request, context.message)
    return HTTPFound(location = "/")

def logged_in(context, request):
    """ Handle login through another service. Note that this is not the same as a local login.
        A cookie still needs to be set. Also, it's possible to run this method for a user that's
        already logged in locally, ie wanting to connect to a another service to use it as auth.
    """
    userid = request.authenticated_userid
    auth_info = get_auth_info(request)
    if not auth_info:
        raise HTTPForbidden("No auth session in progress")
    if 'error' in auth_info:
        _try_to_add_error(request, auth_info['error'])
        return HTTPFound(location = "/")
    auth_method = request.registry.queryMultiAdapter((context, request),
                                                     IPluggableAuth,
                                                     name = auth_info['provider_type'])
    if not auth_method:
        raise HTTPForbidden("There's no login provider called '%s'" % auth_info['provider_type'])
    if not userid:
        appstruct = auth_method.appstruct(auth_info)
        try:
            return auth_method.login(appstruct)
        except UserNotFoundError:
            #May need to register?
            url = auth_method.registration_url(token = request.params['token'])
            return HTTPFound(location = url)
    else:
        user = context['users'][userid]
        auth_method.set_auth_domain(user, auth_info['provider_type'])
        url = request.resource_url(context)
        return HTTPFound(location = url)


class RegisterPASView(BaseForm):
    type_name = 'Auth'
    schema_name = 'pas_register'
    title = _(u"Complete registration")

    def __init__(self, context, request):
        super(RegisterPASView, self).__init__(context, request)
        if request.authenticated_userid != None:
            raise HTTPForbidden(_(u"Already logged in"))
        if not context.site_settings.get('allow_self_registration', False):
            raise HTTPForbidden(_(u"Site doesn't allow self registration"))
        auth_info = get_auth_info(request)
        if not auth_info:
            raise HTTPForbidden(_("Can't find any ongoing authentication session. Please try again!"))

    def __call__(self):
        response = super(RegisterPASView, self).__call__()
        #Just register or do we have a schema?
        if self.schema.children:
            return response
        return self.register_success({})

    @property
    def buttons(self):
        return (deform.Button('register', title = _(u"Register"), css_class = 'btn btn-primary'),
                 self.button_cancel,)

    def register_success(self, appstruct):
        self.flash_messages.add(_(u"Welcome, you're now registered!"), type="success")
        factory = self.get_content_factory('User')
        userid = appstruct.pop('userid', None)
        obj = factory(**appstruct)
        if userid is None: #In case someone removed the userid from the schema
            userid = obj.uid
        self.context['users'][userid] = obj
        auth_info = get_auth_info(self.request)
        auth_method = self.request.registry.queryMultiAdapter((self.context, self.request),
                                                         IPluggableAuth,
                                                         name = auth_info['provider_type'])
        auth_method.set_auth_domain(obj, auth_info['provider_type'])
        headers = remember(self.request, obj.userid)
        return HTTPFound(location = self.request.resource_url(obj), headers = headers)
