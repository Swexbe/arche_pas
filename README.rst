Arche pluggable authentication service README
=============================================

Service for authentication using requests-oauthlib.

New providers are registered by subclassing arche_pas.models.PASProvider and config.add_pas(<YourProviderClass>).

Providers are initialized in your paster .ini using:


arche.includes =
    # To activate PAS module.
    arche_pas


# Activate provider 'google_oauth2' with data from var/google.json

arche_pas.providers
    arche_pas.providers.google_oauth2 %(here)s/../var/google.json


Example json setting file (google.json from above):

{"client_id":"<your-client-id>",
  "project_id":"<your-project-id>",
  "auth_uri":"https://accounts.google.com/o/oauth2/auth",
  "token_uri":"https://accounts.google.com/o/oauth2/token",
  "client_secret":"<your-client-secret>"
  }


Get login url for a provider, in this case Google OAuth2, using pyramids route_url:

request.route_url('pas_begin', provider="google_oauth2")
