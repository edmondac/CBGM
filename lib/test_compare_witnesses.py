from unittest import TestCase
from .compare_witnesses import Attestations
from . import test_db
from .test_logging import default_logging
default_logging()


class TestAttestations(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db = test_db.TestDatabase()
        cls.attestations = Attestations(cls.test_db.db_file)

    @classmethod
    def tearDownClass(cls):
        cls.test_db.cleanup()

    def test_compare(self):
        self.fail()

    def test_get_attestations(self):
        self.fail()
