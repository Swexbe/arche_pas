from logging import getLogger

from pyramid.i18n import TranslationStringFactory
from pyramid.settings import asbool


logger = getLogger(__name__)
_ = TranslationStringFactory('arche_pas')


DEFAULTS = {
    #Allow HTTP? Good for debug reasons, not good for anything else
    'arche_pas.insecure_transport': False,
}


def includeme(config):
    bools = ('arche_pas.insecure_transport',)
    settings = config.registry.settings
    for (k, v) in DEFAULTS.items():
        if k not in settings:
            settings[k] = v
    for k in bools:
        settings[k] = asbool(settings[k])
    if settings['arche_pas.insecure_transport']:
        import os
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    config.include('.models')
    config.include('.catalog')
    config.include('.views')
    config.include('.schemas')
    #Check for providers and include them
    for k in config.registry.settings:
        if k.startswith('arche_pas.providers.'):
            config.include(k)
