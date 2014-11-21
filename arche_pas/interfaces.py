from zope.interface import Interface
from pyramid.interfaces import IDict
from arche.interfaces import IContextAdapter


class IProviderData(IDict, IContextAdapter):
    """ Adapts an IUser object and stores information from authentication
        providers.
    """

class IPluggableAuth(Interface):

    def registration_url(**kw):
        """ Get the URL used for registration with this provider. """

    def render_login():
        """ Render login button or form. """

    def appstruct(auth_info):
        """ Get appstruct for login or registration. """

    def login(appstruct):
        """ Login user or raise UserNotFound exception, which normally means someone should register. """

    def set_auth_domain(user, domain, **kw):
        """ Store authentication data for a domain. """
        