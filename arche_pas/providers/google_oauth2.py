from requests_oauthlib import OAuth2Session
from six import string_types

from arche_pas.models import PASProvider
from arche_pas import _


class GoogleOAuth2(PASProvider):
    name = "google_oauth2"
    title = _("Google")
    id_key = 'id'
    paster_config_ns = __name__
    trust_email = True
    default_settings = {
        "auth_uri":"https://accounts.google.com/o/oauth2/auth",
        "token_uri":"https://accounts.google.com/o/oauth2/token",
        "scope":["https://www.googleapis.com/auth/userinfo.email",
                 "https://www.googleapis.com/auth/userinfo.profile"],
        "profile_uri":"https://www.googleapis.com/oauth2/v1/userinfo",
        "access_type":"offline",
        "approval_prompt":"force"
    }

    @classmethod
    def validate_settings(cls):
        try:
            assert isinstance(cls.settings, dict), \
                "No configuration found for provider %r" % cls.name
            assert isinstance(cls.settings.get('scope', None), list)
            for str_k in ('client_id', 'project_id', 'auth_uri', 'token_uri', 'client_secret'):
                assert isinstance(cls.settings.get(str_k, None), string_types), \
                    "Missing config key %r for provider %r" % (str_k, cls.name)
        except AssertionError as exc:
            raise cls.ProviderConfigError(exc.message)

    def get_session(self):
        return OAuth2Session(self.settings['client_id'],
                             scope=self.settings['scope'],
                             redirect_uri=self.callback_url())

    def begin(self):
        # OAuth endpoints given in the Google API documentation
        google = self.get_session()
        authorization_url, state = google.authorization_url(self.settings['auth_uri'],
                                                            access_type=self.settings['access_type'],
                                                            approval_prompt=self.settings['approval_prompt'])
        return authorization_url

    def callback(self):
        google = self.get_session()
        #Should we do anything with the token response? Auth is handled by Arche anyway.
        #We should probably store the image url
        res =  google.fetch_token(self.settings['token_uri'],
                                  client_secret=self.settings['client_secret'],
                                  authorization_response=self.request.url)
        profile_response = google.get(self.settings['profile_uri'])
        profile_data = profile_response.json()
        return profile_data

    def get_email(self, response, validated=False):
        email = response.get('email', None)
        if email:
            if validated:
                if response.get('verified_email', False):
                    return email
            else:
                return email

    def registration_appstruct(self, response):
        return dict(
            first_name = response.get('given_name', ''),
            last_name = response.get('family_name', '')
        )


def includeme(config):
    config.add_pas(GoogleOAuth2)
