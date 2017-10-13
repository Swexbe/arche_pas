
class ProviderConfigError(Exception):
    """ Validation of required configuration failed.
    """


class RegistrationCaseMissmatch(Exception):
    """ Raised when fetching registration cases if they don't match.
    """
