from arche.interfaces import IUser
from pyramid.httpexceptions import HTTPFound
from pyramid.security import remember

from arche_pas import _
from arche_pas.exceptions import UserNotFoundError
from arche_pas.interfaces import IProviderData
from arche_pas.models import BasePluggableAuth
from arche_pas.models import get_auth_info


class OpenIDAuth(BasePluggableAuth):
    name = 'openid'
    title = _(u"OpenID")
    renderer = "arche_pas:templates/openid.pt"
 
    def appstruct(self, auth_info):
        result = dict(
            openid_username = auth_info['profile']['accounts'][0]['username'],
        )
        #FIXME: Make this configurable through attribute exchange...
        try:
            result['email'] = auth_info['profile']['verifiedEmail']
        except KeyError:
            pass
        return result
   
    def login(self, appstruct):
        user = self.context.users.get_auth_domain_user(self.name, 'openid_username', appstruct['openid_username'])
        if user:
            headers = remember(self.request, user.userid)
            url = appstruct.get('came_from', None)
            if url is None:
                url = self.request.resource_url(self.context)
            raise HTTPFound(location = url,
                             headers = headers)
        raise UserNotFoundError()

    def set_auth_domain(self, user, domain, **kw):
        assert domain == self.name
        assert IUser.providedBy(user)
        auth_info = get_auth_info(self.request)
        reg_data = self.appstruct(auth_info)
        kw['openid_username'] = reg_data['openid_username']
        pd = IProviderData(user)
        pd[domain] = kw


def add_openid_from_settings(config, prefix='velruse.openid.'):
    from velruse.settings import ProviderSettings
    settings = config.registry.settings
    p = ProviderSettings(settings, prefix)
    p.update('realm')
    p.update('storage')
    p.update('login_path')
    p.update('callback_path')
    config.add_openid_login(**p.kwargs)


def includeme(config):
    config.registry.registerAdapter(OpenIDAuth, name = OpenIDAuth.name)
