from requests_oauthlib import OAuth2Session

from arche_pas.models import PASProvider
from arche_pas import _


#FIXME: Not done yet

class WPOauth2(PASProvider):
    name = "wp_oauth2"
    title = _("OAuth2")
    id_key = 'ID'
    paster_config_ns = __name__
    default_settings = {}
    trust_email = False

    def begin(self):
        auth_session = OAuth2Session(
            client_id=self.settings['client_id'],
            #scope=self.settings['scope'],
            redirect_uri=self.callback_url()
        )
        authorization_url, state = auth_session.authorization_url(
            self.settings['auth_uri'],
            #access_type=self.settings['access_type'],
            #response_type='code',
            #approval_prompt=self.settings['approval_prompt']
        )
       # authorization_url = """https://naturkontakt.naturskyddsforeningen.se/oauth/authorize?response_type=code&client_id=IfbcOXbRndssPv1uyTdTqzKN7nk9CQAk6MxVKIM7&response_type=code&redirect_uri=http://localhost:6543/pas_callback/naturkontakt"""
        return authorization_url

    def callback(self):
        auth_session = OAuth2Session(
            client_id=self.settings['client_id'],
            redirect_uri=self.callback_url()
        )
        #Use token response any other way?
        res = auth_session.fetch_token(
            self.settings['token_uri'],
            code=self.request.GET.get('code', ''),
            #grant_type='authorization_code',
            client_secret=self.settings['client_secret'],
        )
        profile_response = auth_session.get(self.settings['profile_uri'])
        profile_data = profile_response.json()
        print "\n\n"
        print profile_data
        return profile_data

    def get_email(self, response, validated=False):
        email = response.get('user_email', None)
        if email:
            #Email validation doesn't seem to be part of WP?
            if not validated:
                return email

    def registration_appstruct(self, response):
        names = response.get('display_name', "").split()
        email = self.get_email(response)
        if not email:
            email = ''
        return dict(
            first_name = " ".join(names[:1]),
            last_name = " ".join(names[1:]),
            email = email,
        )


def includeme(config):
    config.add_pas(WPOauth2)
