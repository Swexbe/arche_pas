from UserDict import IterableUserDict

from BTrees.OOBTree import OOBTree
from arche.interfaces import IRoot
from arche.interfaces import IUser
from pyramid.httpexceptions import HTTPFound
from pyramid.interfaces import IRequest
from pyramid.security import remember
from zope.component import adapter
from zope.interface import implementer
from velruse import login_url
from pyramid.renderers import render

from arche_pas import _
from arche_pas.interfaces import IProviderData
from arche_pas.interfaces import IPluggableAuth
from arche_pas.exceptions import UserNotFoundError


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

    def __repr__(self):
        klass = self.__class__
        classname = '%s.%s' % (klass.__module__, klass.__name__)
        return '<%s adapting %s containing %s items>' % (classname,
                                                   self.context,
                                                   len(self))


@implementer(IPluggableAuth)
@adapter(IRoot, IRequest)
class BasePluggableAuth(object):
    name = ""
    renderer = "arche_pas:templates/button.pt"

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def login_url(self):
        return login_url(self.request, self.name)

    def registration_url(self, **kw):
        return self.request.route_url('pas_register', provider_name = self.name, _query = kw)

    def render_login(self):
        response = {'login_url': self.login_url(),
                    'provider': self}
        return render(self.renderer, response, request = self.request)

    def appstruct(self, auth_info):
        return {}

    def login(self, appstruct):
        raise NotImplementedError()

    def set_auth_domain(self, user, domain, **kw):
        raise NotImplementedError()
        

class BaseOAuth2Plugin(BasePluggableAuth):

    def appstruct(self, auth_info):
        result = dict(
            oauth_token = auth_info['credentials']['oauthAccessToken'],
            oauth_userid = auth_info['profile']['accounts'][0]['userid'],
        )
        try:
            result['email'] = auth_info['profile']['verifiedEmail']
        except KeyError:
            pass
        return result
  
    def login(self, appstruct):
        user = get_auth_domain_user(self.context, self.name, 'oauth_userid', appstruct['oauth_userid'])
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
        kw['oauth_userid'] = reg_data['oauth_userid']
        pd = IProviderData(user)
        pd[domain] = kw


def get_auth_info(request):
    token = request.params.get('token', '')
    storage = request.registry.velruse_store
    try:
        return storage.retrieve(token)
    except KeyError:
        return {}


def get_auth_domain_user(root, domain, key, value):
    """ Currently loops through users to find first matching user for login.
        This is a bad idea for large sites, so we need to cache this eventually.
    """
    users = root['users']
    marker = object()
    for user in users.values():
        pd = IProviderData(user, None)
        if pd and pd.get(domain, {}).get(key, marker) == value:
            return user


def includeme(config):
    config.registry.registerAdapter(ProviderData)
