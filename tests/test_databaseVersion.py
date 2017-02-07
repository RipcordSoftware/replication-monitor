from unittest import TestCase

from src.couchdb import CouchDB


class TestDatabaseVersion(TestCase):
    def test_simple_parse(self):
        ver = CouchDB.DatabaseVersion("1.2.3")
        self.assertTrue(ver.valid)
        self.assertEqual("1.2.3", ver.version)
        self.assertEqual(1, ver.major)
        self.assertEqual(2, ver.minor)
        self.assertEqual(3, ver.build)

    def test_invalid1(self):
        ver = CouchDB.DatabaseVersion("a.b.c")
        self.assertFalse(ver.valid)
        self.assertIsNone(ver.version)

    def test_invalid2(self):
        ver = CouchDB.DatabaseVersion("1.b.c")
        self.assertFalse(ver.valid)
        self.assertIsNone(ver.version)

    def test_invalid3(self):
        ver = CouchDB.DatabaseVersion("1.2.3.4")
        self.assertFalse(ver.valid)
        self.assertIsNone(ver.version)

    def test_invalid4(self):
        ver = CouchDB.DatabaseVersion("")
        self.assertFalse(ver.valid)
        self.assertIsNone(ver.version)

    def test_invalid5(self):
        ver = CouchDB.DatabaseVersion(1.1)
        self.assertFalse(ver.valid)
        self.assertIsNone(ver.version)

    def test_None(self):
        ver = CouchDB.DatabaseVersion(None)
        self.assertFalse(ver.valid)
        self.assertIsNone(ver.version)