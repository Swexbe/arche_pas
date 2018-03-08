import unittest
from os import path
from pyramid import testing
from zope.interface.verify import verifyObject
from zope.interface.verify import verifyClass
from pyramid.request import apply_request_extensions


here_path = path.dirname(path.realpath(__file__))
dummy_file = path.join(here_path, "provider_dummy.json")


class InitTests(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def test_read_config(self):
        from arche_pas import format_providers
        txt = """
            hello_provider	{fn}
            maybe_provider {fn}
        """.format(fn=dummy_file)
        results = format_providers(txt)
        self.assertEqual(set(results.keys()), set(['hello_provider', 'maybe_provider']))
        self.assertEqual(results['hello_provider'], dummy_file)
