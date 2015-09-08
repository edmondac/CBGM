# encoding: utf-8

import re

# Constants representing reading relationships (used internally)
PRIOR = "PRIOR"
POSTERIOR = "POSTERIOR"
NOREL = "NOREL"
EQUAL = "EQUAL"

# Constants for the user to define reading relationships
INIT = "INIT"
UNCL = "UNCL"


def sort_mss(ms_list):
    """
    Return a sorted list of manuscripts - A first, then Papyri, then majuscules
    in order.
    """
    def witintify(x):
        # return an inte representing this witness
        if x.startswith('0'):
            return 20000 + int(re.search('([0-9]+)', x).group(1))
        elif x.startswith('P'):
            return 10000 + int(re.search('([0-9]+)', x).group(1))
        elif x == 'A':
            return 1
        else:
            raise ValueError("What? {}".format(x))

    return sorted(ms_list, key=lambda x: witintify(x))


def pretty_p(x):
    """
    Turns P into a gothic 𝔓
    """
    if x.startswith('P'):
        x = u'𝔓{}'.format(x[1:])
    return x


def sorted_vus(cursor, sql=None):
    """
    Return a full list of variant units, properly sorted.
    """
    def numify(vu):
        a, b = vu.split('/')
        if '-' in b:
            bits = [int(x) for x in b.split('-')]
            b = float("{}.{}".format(*bits))
        else:
            b = int(b)
        a = int(a)
        return [a, b]

    if sql is None:
        sql = 'SELECT DISTINCT variant_unit FROM reading'

    return sorted([x[0] for x in cursor.execute(sql)],
                  key=lambda s: numify(s))
