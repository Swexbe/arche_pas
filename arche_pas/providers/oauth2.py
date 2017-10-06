from requests_oauthlib import OAuth2Session

from arche_pas.models import PASProvider
from arche_pas import _


#FIXME: Not done yet

class OAuth2Generic(PASProvider):
    name = "oauth2"
    title = _("OAuth2")
    id_key = 'id'
    paster_config_ns = __name__
    default_settings = {}

    def get_session(self):
        return OAuth2Session(self.settings['client_id'],
                             #scope=self.settings['scope'],
                             redirect_uri=self.callback_url())

    def begin(self):
        auth_session = self.get_session()
        authorization_url, state = auth_session.authorization_url(self.settings['auth_uri'],
                                                            #access_type=self.settings['access_type'],
                                                            #approval_prompt=self.settings['approval_prompt']
        )
        return authorization_url

    def callback(self):
        auth_session = self.get_session()
        #Should we do anything with the token response? Auth is handled by Arche anyway.
        res = auth_session.fetch_token(self.settings['token_uri'],
                                client_secret=self.settings['client_secret'],
                                authorization_response=self.request.url)
        profile_response = auth_session.get(self.settings['profile_uri'])
        profile_data = profile_response.json()
        return profile_data

    def get_validated_email(self, response):
        response.get('user_email', None)
        # if response.get('verified_email', False):
        #     email = response.get('email', None)
        #     if email:
        #         return email

    def registration_appstruct(self, response):
        return dict(
            first_name = response.get('given_name', ''),
            last_name = response.get('family_name', '')
        )


def includeme(config):
    config.add_pas(OAuth2Generic)
