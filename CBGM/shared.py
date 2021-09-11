# encoding: utf-8

import re
import string
import logging

logger = logging.getLogger(__name__)

# Constants representing reading relationships (used internally)
PRIOR = "PRIOR"
POSTERIOR = "POSTERIOR"
NOREL = "NOREL"
EQUAL = "EQUAL"

# Constants for the user to define reading relationships
INIT = "INIT"  # The initial text
# The parent reading in an overlapped unit. This is used where the overlapping
# unit has an omission as INIT, and so the initial text is lacunose in the
# overlapped units.
OL_PARENT = "OL_PARENT"
UNCL = "UNCL"  # Unclear
LAC = "LAC"  # Lacuna


re_vref = re.compile("B([0-9]+)K([0-9]+)V([0-9]+)")
re_context = re.compile(r"[^.]+\.(\d+|\w+)\.?(\d+)?")


def memoize(f):
    """
    Based on http://www.python-course.eu/python3_memoization.php

    WARNING - this can cause effective memory leaks in long running processes
    """
    memo = {}

    def helper(*x):
        if x not in memo:
            memo[x] = f(*x)
        return memo[x]
    return helper


def witintify(x):
    # return a sortable tuple representing this witness
    num_match = re.search('([0-9]+)', x)
    if num_match:
        num = int(num_match.group(1))
        rem = x.replace(num_match.group(1), '')
    else:
        num = 0
        rem = x

    if x.startswith('0'):
        offset = 20000
    elif x.startswith('P'):
        offset = 10000
    elif x == 'A':
        num = 1
        offset = 0
    elif x.startswith('L'):
        offset = 40000
    elif x[0] in string.digits:
        offset = 30000
    else:
        offset = 0

    return (offset + num, rem)


def sort_mss(ms_list):
    """
    Return a sorted list of manuscripts - A first, then Papyri, then majuscules
    in order.
    """
    return sorted(ms_list, key=lambda x: witintify(x))


def pretty_p(x):
    """
    Turns P into a gothic 𝔓
    """
    if 'P' in x:
        x = x.replace('P', '𝔓')
    return x


def numify(vu):
    """
    Turn a variant unit into a pair of integers that can be sorted

    A variant unit will be something like:
        * Simple case: B04K01V04/5-7
        * Composite case: B04K01V50/2-36,B04K01V51/2-22,B04K01V52/2-6
    """
    a, b = vu.split('/', 1)

    # For composite variant units, we'll lose everything after the comma
    b = b.split(',')[0]

    if '-' in b:
        bits = [int(x) for x in b.split('-')]
        b = float("{}.{}".format(*bits))
    else:
        b = int(b)

    if re_vref.match(a):
        # This is a full ref
        bits = [int(x) for x in re_vref.match(a).groups()]
        a = 100000 * bits[0] + 1000 * bits[1] + bits[2]
    elif re_context.match(a):
        # this is the context
        bits = [x for x in re_context.match(a).groups()]
        if bits[0] == 'inscriptio':
            a = 100000 + 1000 * 0 + 0
        elif bits[0] == 'subscriptio':
            a = 100000 + 1000 * 99 + 0
        else:
            a = 100000 + 1000 * int(bits[0]) + int(bits[1])
    else:
        # Assume it's a simple verse number
        a = int(a)

    return [a, b]


def sorted_vus(cursor, sql=None):
    """
    Return a full list of variant units, properly sorted.
    """
    if sql is None:
        sql = 'SELECT DISTINCT variant_unit FROM cbgm'

    return sorted([x[0] for x in cursor.execute(sql)],
                  key=lambda s: numify(s))
