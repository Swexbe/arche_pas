Arche pluggable authentication service
======================================

Fork of https://github.com/ArcheProject/arche\_pas with support for Gamma
-------------------------------------------------------------------------

Service for authentication using requests-oauthlib.

Providers are initialized in your paster .ini using:

| arche.includes =
|     # To activate PAS module.
|     arche\_pas

# Activate provider 'google\_oauth2' with data from var/google.json

| arche\_pas.providers
|     arche\_pas.providers.gamma %(here)s/../var/gamma.json

Example json setting file (gamma.json from above):

::

    {
      "client_id": "%GAMMA_CLIENT_ID%",
      "auth_uri": "%GAMMA_AUTH_URI%",
      "token_uri": "%GAMMA_TOKEN_URI%",
      "client_secret": "%GAMMA_CLIENT_SECRET%",
      "profile_uri": "%GAMMA_PROFILE_URI%"
    }

