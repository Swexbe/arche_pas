from requests_oauthlib import OAuth2Session

from arche_pas.models import PASProvider
from arche_pas import _


class GammaOAuth2(PASProvider):
    name = "gamma"
    title = _("Gamma")
    id_key = 'id'
    paster_config_ns = __name__
    default_settings = {
        "auth_uri": "https://gamma.chalmers.it/api/oauth/authorize",
        "token_uri": "https://gamma.chalmers.it/api/oauth/token",
        "profile_uri": "https://gamma.chalmers.it/api/users/me",
    }
    trust_email = True
    f = open('/app/var/whitelist.txt', "r");
    whitelist = f.read().splitlines();

    def begin(self):
        auth_session = OAuth2Session(
            client_id=self.settings['client_id'],
            # scope=self.settings['scope'],
            redirect_uri=self.callback_url()
        )
        authorization_url, state = auth_session.authorization_url(
            self.settings['auth_uri'],
        )
        return authorization_url

    def callback(self):
        auth_session = OAuth2Session(
            client_id=self.settings['client_id'],
            redirect_uri=self.callback_url()
        )
        # Use token response any other way?
        res = auth_session.fetch_token(
            self.settings['token_uri'],
            code=self.request.GET.get('code', ''),
            client_secret=self.settings['client_secret'],
        )
        profile_response = auth_session.get(self.settings['profile_uri'])
        profile_data = profile_response.json()
        return profile_data

    def get_email(self, response, validated=False):
        email = response.get('email', None);
        cid = response.get('cid', None);
        if cid not in self.whitelist:
            raise Exception("User not in whitelist")
        return email

    def get_profile_image(self, response):
        url = response.get('avatarUrl', "")
        if url:
            return url

    def registration_appstruct(self, response):
        fname = response.get('firstName', "")
        lname = response.get('lastName', "")
        nick = response.get('nick', "")
        email = self.get_email(response)
        if not email:
            email = ''
        return dict(
            first_name=fname + " '" + nick + "'",
            last_name=lname,
            email=email,
        )


def includeme(config):
    config.add_pas(GammaOAuth2)
