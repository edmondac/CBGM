from unittest import TestCase

from CBGM import shared


@shared.memoize
def test_memoize_fn(arg):
    test_memoize_fn.executed += 1
    return "<%s>" % arg
test_memoize_fn.executed = 0


@shared.memoize
def test_memoize_fn2(arg1, arg2):
    test_memoize_fn2.executed += 1
    return "%s :: %s" % (arg1, arg2)
test_memoize_fn2.executed = 0


class TestShared(TestCase):
    def test_memoize_1_arg(self):
        """
        Test our memoize decorator with a single argument
        """
        ret = test_memoize_fn(1)
        self.assertEqual(ret, "<1>")
        self.assertEqual(test_memoize_fn.executed, 1)

        ret2 = test_memoize_fn(1)
        self.assertEqual(ret2, "<1>")
        self.assertEqual(test_memoize_fn.executed, 1)

        ret3 = test_memoize_fn(99)
        self.assertEqual(ret3, "<99>")
        self.assertEqual(test_memoize_fn.executed, 2)

    def test_memoize_2_args(self):
        """
        Test our memoize decorator with two arguments
        """
        ret = test_memoize_fn2(1, 2)
        self.assertEqual(ret, "1 :: 2")
        self.assertEqual(test_memoize_fn2.executed, 1)

        ret2 = test_memoize_fn2(1, 2)
        self.assertEqual(ret2, "1 :: 2")
        self.assertEqual(test_memoize_fn2.executed, 1)

        ret3 = test_memoize_fn2(99, 100)
        self.assertEqual(ret3, "99 :: 100")
        self.assertEqual(test_memoize_fn2.executed, 2)

    def test_witintify(self):
        """
        Check that the witintify function does what's expected of it
        """
        data = [
            ('A', 1, 'A'),
            ('P75', 10075, 'P'),
            ('04', 20004, ''),
            ('032S', 20032, 'S'),
            ('13', 30013, ''),
            ('1008C*', 31008, 'C*'),
            ('L123-5W2S', 40123, 'L-5W2S'),
        ]
        for data_in, data_out, rem in data:
            self.assertEqual((data_out, rem), shared.witintify(data_in))

    def test_sort_mss(self):
        """
        Check that manuscripts are sorted properly
        """
        data = [
            (('01', 'L1', '1', 'P1', 'A'), ['A', 'P1', '01', '1', 'L1']),
            (('P1', 'P4', 'P2'), ['P1', 'P2', 'P4']),
        ]
        for data_in, data_out in data:
            self.assertEqual(data_out, shared.sort_mss(data_in))

    def test_pretty_p(self):
        """
        Check gothic P turns up
        """
        self.assertEqual('abcd0', shared.pretty_p('abcd0'))
        self.assertEqual('a𝔓bc𝔓d0', shared.pretty_p('aPbcPd0'))

    def test_numify(self):
        """
        Check that variant unit identifiers are properly turned into sortable tuples of numbers
        """
        # Simple case: B04K01V04/5-7
        self.assertEqual([401004, 5.7], shared.numify('B04K01V04/5-7'))
        # Composite case: B04K01V50/2-36,B04K01V51/2-22,B04K01V52/2-6
        self.assertEqual([401050, 2.36], shared.numify('B04K01V50/2-36,B04K01V51/2-22,B04K01V52/2-6'))

