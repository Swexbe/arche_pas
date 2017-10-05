import unittest

from BTrees.OOBTree import OOBTree
from arche.interfaces import IUser, IObjectUpdatedEvent
from arche.testing import barebone_fixture
from pyramid import testing
from zope.interface.verify import verifyObject
from zope.interface.verify import verifyClass
from arche.api import User
from pyramid.request import apply_request_extensions

from arche_pas.interfaces import IProviderData
from arche_pas.interfaces import IPASProvider
from arche_pas.exceptions import ProviderConfigError


class ProviderDataTests(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()
 
    def tearDown(self):
        testing.tearDown()
 
    @property
    def _cut(self):
        from arche_pas.models import ProviderData
        return ProviderData

    def test_verify_object(self):
        context = User()
        self.failUnless(verifyObject(IProviderData, self._cut(context)))
 
    def test_verify_class(self):
        self.failUnless(verifyClass(IProviderData, self._cut))

    def test_setitem(self):
        context = User()
        obj = self._cut(context)
        obj['one'] = {'one': 1}
        self.assertIsInstance(obj['one'], OOBTree)


class PASProviderTests(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche_pas.models import PASProvider
        return PASProvider

    def _dummy_provider(self):
        class DummyProvider(self._cut):
            name = 'dummy'
            title = 'Wakka'
            _settings = None
            id_key = 'dummy_key'
            default_settings = {'one': 1}
            @classmethod
            def validate_settings(cls):
                if cls.settings.get('one') != 1:
                    raise ProviderConfigError()
        return DummyProvider

    def test_verify_object(self):
        context = testing.DummyModel()
        self.failUnless(verifyObject(IPASProvider, self._cut(context)))

    def test_verify_class(self):
        self.failUnless(verifyClass(IPASProvider, self._cut))

    def test_settings(self):
        factory = self._dummy_provider()
        factory.update_settings({'two': 2}, three=3)
        obj = factory(testing.DummyModel())
        self.assertEqual(obj.settings, {'one': 1, 'two': 2, 'three': 3})

    def test_validate_settings(self):
        factory = self._dummy_provider()
        factory.update_settings(one=2)
        self.assertRaises(ProviderConfigError, factory.validate_settings)

    def test_get_id(self):
        self.config.include('arche_pas.models')
        user = User()
        provider_data = IProviderData(user)
        provider_data['dummy'] = {'dummy_key': 'very_secret'}
        obj = self._dummy_provider()(testing.DummyModel())
        self.assertEqual(obj.get_id(user), 'very_secret')

    def test_get_user(self):
        self.config.include('arche.testing')
        self.config.include('arche.testing.catalog')
        self.config.include('arche_pas')
        root = barebone_fixture(self.config)
        request = testing.DummyRequest()
        apply_request_extensions(request)
        request.root = root
        user = User()
        provider_data = IProviderData(user)
        provider_data['dummy'] = {'dummy_key': 'very_secret'}
        provider = self._dummy_provider()
        self.config.registry.registerAdapter(provider, name = provider.name)
        root['users']['jane'] = user
        query = "pas_ident == ('dummy', 'very_secret')"
        docids = root.catalog.query(query)[1]
        self.assertEqual(tuple(request.resolve_docids(docids))[0], user)
        obj = provider(root)
        self.assertEqual(obj.get_user(request, 'very_secret'), user)

    # def prepare_register(self, request, data):
    #
    # def login(self, user, request, first_login = False, came_from = None):
    #
    def test_store(self):
        self.config.include('arche.testing')
        self.config.include('arche.testing.catalog')
        self.config.include('arche_pas')
        root = barebone_fixture(self.config)
        request = testing.DummyRequest()
        apply_request_extensions(request)
        request.root = root
        user = User()
        provider_data = IProviderData(user)
        provider_data['dummy'] = {'dummy_key': 'very_secret'}
        provider = self._dummy_provider()
        self.config.registry.registerAdapter(provider, name = provider.name)
        root['users']['jane'] = user
        obj = provider(root)
        L = []
        def subsc(obj, event):
            L.append(event)
        self.config.add_subscriber(subsc, [IUser, IObjectUpdatedEvent])
        obj.store(user, {'hello': 'world', 1:2})
        self.assertIn('pas_ident', L[0].changed)


class AddPASTests(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _fut(self):
        from arche_pas.models import add_pas
        return add_pas

    #FIXME: Proper tests for add_pas
