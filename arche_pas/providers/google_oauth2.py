from pyramid.renderers import render
from velruse import login_url

from arche_pas.models import BaseOAuth2Plugin
from arche_pas import _


class GoogleOAuth2(BaseOAuth2Plugin):
    name = 'google_oauth2'
    title = _(u"Google")

    def render_login(self):
        response = {'login_url': login_url(self.request, 'google'),
                    'provider': self}
        return render(self.renderer, response, request = self.request)


def includeme(config):
    config.registry.registerAdapter(GoogleOAuth2, name = GoogleOAuth2.name)
