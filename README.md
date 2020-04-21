# Arche pluggable authentication service

## Fork of https://github.com/ArcheProject/arche_pas with support for Gamma

Service for authentication using requests-oauthlib.

Providers are initialized in your paster .ini using:

arche.includes =\
&nbsp;&nbsp;&nbsp;&nbsp;# To activate PAS module.\
&nbsp;&nbsp;&nbsp;&nbsp;arche_pas

\# Activate provider 'google_oauth2' with data from var/google.json

arche_pas.providers\
&nbsp;&nbsp;&nbsp;&nbsp;arche_pas.providers.gamma %(here)s/../var/gamma.json

Example json setting file (gamma.json from above):

```
{
  "client_id": "%GAMMA_CLIENT_ID%",
  "auth_uri": "%GAMMA_AUTH_URI%",
  "token_uri": "%GAMMA_TOKEN_URI%",
  "client_secret": "%GAMMA_CLIENT_SECRET%",
  "profile_uri": "%GAMMA_PROFILE_URI%"
}
```
