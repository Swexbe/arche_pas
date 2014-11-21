import unittest

from pyramid import testing
from zope.interface.verify import verifyObject
from zope.interface.verify import verifyClass
from arche.api import User

from arche_pas.interfaces import IProviderData


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


# class BaseOAuth2PluginTests(unittest.TestCase):
#     def setUp(self):
#         self.config = testing.setUp()
# 
#     def tearDown(self):
#         testing.tearDown()
# 
#     @property
#     def _cut(self):
#         from voteit.velruse.models import BaseOAuth2Plugin
#         return BaseOAuth2Plugin
# 
#     def test_verify_object(self):
#         context = testing.DummyResource()
#         request = testing.DummyRequest()
#         self.failUnless(verifyObject(IAuthPlugin, self._cut(context, request)))
# 
#     def test_verify_class(self):
#         self.failUnless(verifyClass(IAuthPlugin, self._cut))
