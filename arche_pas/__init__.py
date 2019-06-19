from logging import getLogger

from pyramid.i18n import TranslationStringFactory
from pyramid.settings import asbool


logger = getLogger(__name__)
_ = TranslationStringFactory('arche_pas')


DEFAULTS = {
    #Allow HTTP? Good for debug reasons, not good for anything else
    'arche_pas.insecure_transport': False,
}


def format_providers(data):
    """ Read configuration option at arche_pas.providers, which should look something like:
        arche_pas.providers.googe_oauth2 /path/to/config.json
        someotherprovider /path/that/config.json
    """
    results = {}
    if data is None:
        data = []
    elif not isinstance(data, list):
        data = data.splitlines()
    for row in data:
        row = row.strip()
        if row:
            package_name, file_name = row.split(None, 1)
            results[package_name] = file_name.strip()
    return results


def includeme(config):
    from os import environ
    bools = ('arche_pas.insecure_transport',)
    settings = config.registry.settings
    settings['arche_pas.providers'] = providers = format_providers(settings.get('arche_pas.providers', ''))
    if not providers:
        logger.warn("arche_pas.providers isn't set so skipping inclusion of arche_pas")
        return
    for (k, v) in DEFAULTS.items():
        if k not in settings:
            settings[k] = v
    for k in bools:
        settings[k] = asbool(settings[k])
    if settings['arche_pas.insecure_transport']:
        environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        logger.warn('OAuthlib configured to allow insecure transport')
    # FIXME: Make this configurable
    environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
    config.include('.models')
    config.include('.catalog')
    config.include('.views')
    config.include('.schemas')
    config.include('.registration_cases')
    #Check for providers and include them
    for provider_name in providers:
        config.include(provider_name)
    #Translations
    config.add_translation_dirs('arche_pas:locale/')
