from velruse import login_url

from arche_pas.models import BaseOAuth2Plugin
from arche_pas import _


class GoogleOAuth2(BaseOAuth2Plugin):
    name = 'google_oauth2'
    title = _(u"Google")

    def login_url(self):
        return login_url(self.request, 'google')


def includeme(config):
    config.registry.registerAdapter(GoogleOAuth2, name = GoogleOAuth2.name)
