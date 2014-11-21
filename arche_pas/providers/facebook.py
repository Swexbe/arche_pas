from arche_pas.models import BaseOAuth2Plugin
from arche_pas import _


class FacebookAuth(BaseOAuth2Plugin):
    name = 'facebook'
    title = _("Facebook")


def includeme(config):
    config.registry.registerAdapter(FacebookAuth, name = FacebookAuth.name)
