# -*- coding: utf-8 -*-
from unittest import TestCase
from .compare_witnesses import Attestations, variant_unit
from . import test_db
from .test_logging import default_logging

default_logging()

TEST_DATA = """# -*- coding: utf-8 -*-
# This is a made up data set, purely for testing.

from CBGM.lib.populate_db import Reading, LacunaReading, AllBut
from CBGM.lib.shared import UNCL, INIT, OL_PARENT

all_mss = set(['B', 'C', 'D', 'E'])

struct = {
    '21': {
        '2': [
            Reading('a', 'ηθελον', AllBut('B'), INIT),
            Reading('b', 'ηλθον', ['B'], 'a')],
        '6-8': [
            Reading('a', 'λαβειν αυτον', AllBut('C', 'D'), UNCL),
            Reading('b', 'αυτον λαβειν', ['C'], UNCL),
            LacunaReading(['D'])],
    },
    '22': {
        '3': [
            Reading('a', '', AllBut('C'), INIT),
            Reading('b', 'τε', ['C'], 'a')],
        '20': [
            Reading('a', 'ιδων', ['B'], UNCL),
            Reading('b', 'ειδον', ['C'], UNCL),
            Reading('c', 'ειδεν', ['D'], UNCL),
            Reading('d', 'ειδως', ['E'], UNCL)],
    },
    '23': {
        '1': [
            Reading('a', '', AllBut('C', 'B'), INIT),
            Reading('b', 'και', ['B'], 'a'),
            LacunaReading(['C'])],
        '4-10': [
            Reading('a', 'ηλθεν πλοιαρια εκ τιβεριαδος', ['B'], UNCL),
            Reading('b', 'ηλθεν πλοια εκ τιβεριαδος', ['C'], UNCL),
            Reading('c', 'ηλθεν πλοια εκ της τιβεριαδος', ['D', 'E'], UNCL)],
    }
}
"""


class TestAttestations(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db = test_db.TestDatabase(TEST_DATA)
        cls.attestations = Attestations(cls.test_db.db_file)

    @classmethod
    def tearDownClass(cls):
        cls.test_db.cleanup()

    def test_get_attestations(self):
        for (wit, exp) in [
            ('B', {'21/2': variant_unit(label='b', text='ηλθον', parent='a'),
                   '21/6-8': variant_unit(label='a', text='λαβειν αυτον', parent='UNCL'),
                   '22/3': variant_unit(label='a', text='', parent='INIT'),
                   '22/20': variant_unit(label='a', text='ιδων', parent='UNCL'),
                   '23/1': variant_unit(label='b', text='και', parent='a'),
                   '23/4-10': variant_unit(label='a', text='ηλθεν πλοιαρια εκ τιβεριαδος', parent='UNCL')}),
            ('C', {'21/2': variant_unit(label='a', text='ηθελον', parent='INIT'),
                   '21/6-8': variant_unit(label='b', text='αυτον λαβειν', parent='UNCL'),
                   '22/3': variant_unit(label='b', text='τε', parent='a'),
                   '22/20': variant_unit(label='b', text='ειδον', parent='UNCL'),
                   '23/4-10': variant_unit(label='b', text='ηλθεν πλοια εκ τιβεριαδος', parent='UNCL')}),
            ('D', {'21/2': variant_unit(label='a', text='ηθελον', parent='INIT'),
                   '22/3': variant_unit(label='a', text='', parent='INIT'),
                   '22/20': variant_unit(label='c', text='ειδεν', parent='UNCL'),
                   '23/1': variant_unit(label='a', text='', parent='INIT'),
                   '23/4-10': variant_unit(label='c', text='ηλθεν πλοια εκ της τιβεριαδος', parent='UNCL')}),
            ('E', {'21/2': variant_unit(label='a', text='ηθελον', parent='INIT'),
                   '21/6-8': variant_unit(label='a', text='λαβειν αυτον', parent='UNCL'),
                   '22/3': variant_unit(label='a', text='', parent='INIT'),
                   '22/20': variant_unit(label='d', text='ειδως', parent='UNCL'),
                   '23/1': variant_unit(label='a', text='', parent='INIT'),
                   '23/4-10': variant_unit(label='c', text='ηλθεν πλοια εκ της τιβεριαδος', parent='UNCL')})]:
            ret = self.attestations._get_attestations(wit)
            self.assertEqual(exp, ret)

    def test_compare_b_c(self):
        b_c = self.attestations.compare(('B', 'C'))
        exp = """B and C overlap in 5 variant units
> 21/2:
\tB reads ηλθον (b)
\tC reads ηθελον (a)
\t> B has a posterior reading
> 21/6-8:
\tB reads λαβειν αυτον (a)
\tC reads αυτον λαβειν (b)
\t> B and/or C has an unclear relationship
> 22/20:
\tB reads ιδων (a)
\tC reads ειδον (b)
\t> B and/or C has an unclear relationship
> 22/3:
\tB reads  (a)
\tC reads τε (b)
\t> B has a prior reading
> 23/4-10:
\tB reads ηλθεν πλοιαρια εκ τιβεριαδος (a)
\tC reads ηλθεν πλοια εκ τιβεριαδος (b)
\t> B and/or C has an unclear relationship

Summary:
 * B and C agree in 0 variant units
 * B has a prior reading in 1 variant units
 * B has a posterior reading in 1 variant units
 * B and/or C has an unclear relationship in 3 variant units
 * B and C are unrelated in 0 variant units"""
        self.assertEqual(b_c, exp)

    def test_compare_d_e(self):
        d_e = self.attestations.compare(('D', 'E'))
        exp = """D and E overlap in 5 variant units
> 21/2:
\tD reads ηθελον (a)
\tE reads ηθελον (a)
\t> D and E agree
> 22/20:
\tD reads ειδεν (c)
\tE reads ειδως (d)
\t> D and/or E has an unclear relationship
> 22/3:
\tD reads  (a)
\tE reads  (a)
\t> D and E agree
> 23/1:
\tD reads  (a)
\tE reads  (a)
\t> D and E agree
> 23/4-10:
\tD reads ηλθεν πλοια εκ της τιβεριαδος (c)
\tE reads ηλθεν πλοια εκ της τιβεριαδος (c)
\t> D and E agree

Summary:
 * D and E agree in 4 variant units
 * D has a prior reading in 0 variant units
 * D has a posterior reading in 0 variant units
 * D and/or E has an unclear relationship in 1 variant units
 * D and E are unrelated in 0 variant units"""
        self.assertEqual(d_e, exp)
