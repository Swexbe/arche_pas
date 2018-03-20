# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from requests_oauthlib import OAuth2Session
from requests_oauthlib.compliance_fixes import facebook_compliance_fix
from six import string_types

from arche_pas.models import PASProvider
from arche_pas import _


class FacebookOAuth2(PASProvider):
    name = "facebook"
    title = _("Facebook")
    id_key = 'id'
    image_key = 'picture'
    trust_email = True

    default_settings = {
        "auth_uri": "https://www.facebook.com/dialog/oauth",
        "token_uri": "https://graph.facebook.com/oauth/access_token",
        # Scope doesn't seem to have any effect? The profile_uri does however
        "scope": ['email', 'public_profile'],
        "profile_uri":"https://graph.facebook.com/me?fields=id,email,name,picture",
        "approval_prompt":"force"
    }

    @classmethod
    def validate_settings(cls):
        try:
            assert isinstance(cls.settings, dict), \
                "No configuration found for provider %r" % cls.name
            assert isinstance(cls.settings.get('scope', None), list)
            for str_k in ('client_id', 'client_secret', 'auth_uri', 'token_uri', 'profile_uri'):
                assert isinstance(cls.settings.get(str_k, None), string_types), \
                    "Missing config key %r for provider %r" % (str_k, cls.name)
        except AssertionError as exc:
            raise cls.ProviderConfigError(exc.message)

    def get_session(self):
        fb = OAuth2Session(
            self.settings['client_id'],
            scope=self.settings['scope'],
            redirect_uri=self.callback_url()
        )
        facebook_compliance_fix(fb)
        return fb

    def begin(self):
        fb = self.get_session()
        authorization_url, state = fb.authorization_url(
            self.settings['auth_uri'],
            auth_type='rerequest', # Doesn't wolk as far as i can see @2018-03-09
        )
        return authorization_url

    def callback(self):
        fb = self.get_session()
        res = fb.fetch_token(
            self.settings['token_uri'],
            client_secret=self.settings['client_secret'],
            authorization_response=self.request.url
        )
        profile_response = fb.get(self.settings['profile_uri'])
        profile_data = profile_response.json()
        self.logger.debug("FB profile data: %s", profile_data)
        return profile_data

    def get_email(self, response, validated=False):
        return response.get('email', None)

    def registration_appstruct(self, response):
        names = response.get("name", "").split()
        email = self.get_email(response)
        if not email:
            email = ''
        return dict(
            first_name=" ".join(names[:1]),
            last_name=" ".join(names[1:]),
            email=email,
        )

    def get_profile_image(self, response):
        try:
            url = response[self.image_key]['data']['url']
        except KeyError:
            url = None
        if url:
            return url


def includeme(config):
    config.add_pas(FacebookOAuth2)
