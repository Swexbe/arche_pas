from logging import getLogger

from pyramid.i18n import TranslationStringFactory
from pyramid.traversal import find_interface
from arche.interfaces import IRoot

from arche_pas.interfaces import IPluggableAuth


logger = getLogger(__name__)
_ = TranslationStringFactory('arche_pas')


def get_providers(context, request):
    root = find_interface(context, IRoot)
    return request.registry.getAdapters([root, request], IPluggableAuth)


def includeme(config):
    from arche import security
    from velruse.app import auth_complete_view
    from velruse.app import auth_denied_view
    from velruse.app import auth_info_view
    config.include(configure_providers)
    config.include('velruse.app')
    config.commit() #To allow overrides of velruse
    #Override registrations with other permissions
    config.add_view(
        auth_complete_view,
        context = 'velruse.AuthenticationComplete',
        permission = security.NO_PERMISSION_REQUIRED)
    config.add_view(
        auth_denied_view,
        context = 'velruse.AuthenticationDenied',
        permission = security.NO_PERMISSION_REQUIRED)
    config.add_view(
        auth_info_view,
        name = 'auth_info',
        request_param  = 'format=json',
        renderer = 'json',
        permission = security.PERM_MANAGE_SYSTEM)
    config.include('arche_pas.views')
    config.include('arche_pas.models')
    config.include('arche_pas.schemas')
    config.include(include_providers)
   #config.add_translation_dirs('%s:locale/' % PROJECTNAME)

def configure_providers(config):
    logger.debug('Configuring providers')
    import ConfigParser
    from paste.deploy.loadwsgi import NicerConfigParser
    from os.path import isfile
    settings = config.registry.settings
    file_name = settings.get('velruse_providers', 'etc/velruse_providers.ini')
    if not isfile(file_name):
        logger.warn("Can't find any login providers file at: %s - won't add or configure any providers" % file_name)
        return
    parser = ConfigParser.ConfigParser()
    parser.read(file_name)
    if 'velruse_providers' not in parser.sections():
        raise ValueError("Couldn't find any section with [velruse_providers]")
    settings.update(parser.items('velruse_providers'))
    if 'session.secret' not in settings:
        from uuid import uuid4
        settings['session.secret'] =  str(uuid4())
    if 'endpoint' not in settings:
        settings['endpoint'] = '/__pas_logged_in__'
    from velruse.app import settings_adapter
    #This is a hack and should perhaps be filed as a bug report to velruse
    if 'openid' not in settings_adapter:
        from arche_pas.providers.openid import add_openid_from_settings
        settings_adapter['openid'] = 'add_openid_from_settings'
        config.add_directive('add_openid_from_settings',
                             add_openid_from_settings)

def include_providers(config):
    from velruse.app import find_providers
    for provider in find_providers(config.registry.settings):
        #Check for import errors or do this another way?
        name = 'arche_pas.providers.%s' % provider
        logger.info("Including: %s" % name)
        config.include(name)
