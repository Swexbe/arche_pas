

class UserNotFoundError(Exception):
    """ Occurs when a velruse login is performed and no user were returned by the auth tokens.
        Usually means that someone need to register.
    """