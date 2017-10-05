from arche.interfaces import IUser
from pyramid.threadlocal import get_current_registry
from pyramid.traversal import find_root
from repoze.catalog.indexes.keyword import CatalogKeywordIndex

from arche_pas.interfaces import IPASProvider


def get_pas_ident(context, default):
    """ For any user object, index identification for pas method.
        This is a keyword index that contains tuples with
        PAS method name as first item, and the id as the second item.
    """
    if not IUser.providedBy(context):
        return default
    root = find_root(context)
    registry = get_current_registry()
    results = []
    for ar in registry.registeredAdapters():
        if ar.provided == IPASProvider:
           pas_provider = registry.queryAdapter(root, IPASProvider, name = ar.name)
           pas_id = pas_provider.get_id(context)
           if pas_id:
               results.append((pas_provider.name, pas_id))
    if results:
        return results
    return default


def includeme(config):
    indexes = {'pas_ident': CatalogKeywordIndex(get_pas_ident),}
    config.add_catalog_indexes(__name__, indexes)
