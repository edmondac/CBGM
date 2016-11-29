#!/usr/bin/env python
# encoding: utf-8

import re
import sqlite3
from collections import defaultdict


def main(db_file):
    """
    Prints stripes, grouping witnesses by stripe

    @param db_file: db file
    """
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    sql = "SELECT DISTINCT variant_unit FROM cbgm"
    cursor.execute(sql)
    variant_units = [x[0] for x in cursor.fetchall()]

    def intify(x):
        # Return a list of integers for a given vu ident
        return int(re.search('^([0-9]+).*', x).group(1))

    # sort by the two integer parts of the vu
    variant_units.sort(key=lambda s: list(map(intify, s.split('/'))))

    ms_readings = defaultdict(dict)

    sql = """SELECT label, witness, variant_unit FROM cbgm"""
    for label, witness, variant_unit in cursor.execute(sql):
        ms_readings[witness][variant_unit] = label

    ms_stripes = defaultdict(list)
    for wit in ms_readings:
        stripe = []
        for vu in variant_units:
            stripe.append(ms_readings[wit].get(vu, '?'))

        ms_stripes[''.join(stripe)].append(wit)

    def witintify(x):
        # return an int representing this witness
        if x.startswith('0'):
            return 20000 + int(re.search('([0-9]+)', x).group(1))
        elif x.startswith('P'):
            return 10000 + int(re.search('([0-9]+)', x).group(1))
        elif x == 'A':
            return 1
        else:
            raise ValueError("What? {}".format(x))

    r_ms_stripes = {}
    for stripe, wits in list(ms_stripes.items()):
        st_wits = ', '.join(sorted(wits, key=lambda x: witintify(x)))
        r_ms_stripes[st_wits] = stripe

    keys = sorted(list(r_ms_stripes.keys()), key=lambda x: witintify(x))

    for key in keys:
        print('{} {}'.format(key, r_ms_stripes[key]))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Print stripes and highlight duplicates.")
    parser.add_argument('dbfile',
                        help='sqlite db filename (see populate.py)')

    args = parser.parse_args()

    print("Using database: {}".format(args.dbfile))

    main(args.dbfile)
