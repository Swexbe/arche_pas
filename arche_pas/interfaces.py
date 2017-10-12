from arche.interfaces import IContextAdapter
from zope.interface import Interface
from zope.interface import Attribute
from pyramid.interfaces import IDict


class IProviderData(IDict, IContextAdapter):
    """ Adapts an IUser object and stores information from authentication
        providers.
    """


class IPASProvider(Interface):
    """
    """
    name = Attribute("Unique name of adapter")
    title = Attribute("Human-readable name of adapter")
    id_key = Attribute("Where the unique identifier for this user is stored in the providers response.")
    settings = Attribute("Settings")
    default_settings = Attribute("Default settings - will populate settings")
    ProviderConfigError = Attribute("Exception class for configuration errors.")

    def validate_settings():
        """ Validates settings
        """

    def begin():
        """ Start the request to the authorizing server.
            Will return URL where the user should be redirected.
        """

    def callback():
        """ Handle initial response from the auth server and return profile data.
        """

    def callback_url():
        """ Returns the redirect URL, essentially where the server
            should return the user to complete login/registration.
            Known as redirect_uri in OAuth2.
        """

    def get_id(user):
        """
        Get the providers unique identifier for this user.

        :param user: User object
        """

    def get_user(user_ident):
        """ Get any user registered with this identifier.

        :param user_ident: Unique identifier for user.
        :return: User object or None
        """

    def prepare_register(data):
        """
        Either tie an existing user with the same validated email address
        or redirect to registration form.

        :param data: Response data from provider
        :return: HTTPFound, maybe with login headers
        """

    def login(user, first_login = False, came_from = None):
        """
        :param user: User object
        :param first_login: True for users first login. Shouldn't be true when a provider is tied to an existing account.
        :param came_from: Redirect here after login.
        :return: HTTPFound with login headers
        """

    def store(user, data):
        """
        Store provider response and signal the catalog to reindex the 'pas_ident' index.

        :param user: User object
        :param data: provider response data
        :return: None
        """

    def get_email(response, validated=False):
        """
        Return an email address, unvalidated and untrusted.

        :param response: Provider response
        :param validated: Only return email address if the provider claims it's validated.
        :return: email or None
        """

    def registration_appstruct(response):
        """
        :param response: Provider response
        :return: appstruct matching registration schema from providers response data
        """


class IRegistrationCase(Interface):
    """ Figure out how to handle different registration conditions. """
