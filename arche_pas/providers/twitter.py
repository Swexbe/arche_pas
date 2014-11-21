from arche_pas.models import BaseOAuth2Plugin
from arche_pas import _


class TwitterAuth(BaseOAuth2Plugin):
    name = 'twitter'
    title = _("Twitter")


def includeme(config):
    config.registry.registerAdapter(TwitterAuth, name = TwitterAuth.name)
