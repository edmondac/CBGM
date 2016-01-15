#!/usr/bin/env python
# encoding: utf-8

import re
import sqlite3
from collections import defaultdict
from lib.shared import INIT


def main(db_file):
    """
    Prints out all the parts required for a positive apparatus.

    @param db_file: db file
    """
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    sql = "SELECT DISTINCT variant_unit FROM reading"
    cursor.execute(sql)
    variant_units = [x[0] for x in cursor.fetchall()]

    def intify(x):
        # Return a list of integers for a given vu ident
        return int(re.search('^([0-9]+).*', x).group(1))

    # sort by the two integer parts of the vu
    variant_units.sort(key=lambda s: list(map(intify, s.split('/'))))

    #"CREATE TABLE reading (id PRIMARY KEY, variant_unit, label, text, parent);",
    #"CREATE TABLE attestation (reading_id, witness, FOREIGN KEY(reading_id) REFERENCES reading(id));"]

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

    for unit in variant_units:
        sql = "SELECT id, label, text, parent FROM reading WHERE variant_unit = ?"
        cursor.execute(sql, (unit, ))
        def sorter(x):
            if x['parent'] == INIT:
                # This will show up first...
                return '_'
            else:
                return x['label']

        readings = sorted([{'id': x[0],
                            'label': x[1],
                            'text': x[2],
                            'parent': x[3]} for x in cursor.fetchall()],
                          key=sorter)
        print()
        print(unit)
        for reading in readings:
            sql = "SELECT witness FROM attestation WHERE reading_id=?"
            cursor.execute(sql, (reading['id'], ))
            attestations = sorted([x[0] for x in cursor.fetchall()],
                                  key=lambda a: witintify(a))
            print("{} {} {}".format(reading['label'],
                                    reading['text'],
                                    ', '.join(attestations)))



    #~ ms_readings = defaultdict(dict)

    #~ sql = """SELECT label, witness, variant_unit
             #~ FROM attestation, reading
             #~ WHERE attestation.reading_id = reading.id
             #~ """
    #~ for label, witness, variant_unit in cursor.execute(sql):
        #~ ms_readings[witness][variant_unit] = label

    #~ ms_stripes = defaultdict(list)
    #~ for wit in ms_readings:
        #~ stripe = []
        #~ for vu in variant_units:
            #~ stripe.append(ms_readings[wit].get(vu, '?'))

        #~ ms_stripes[''.join(stripe)].append(wit)



    #~ r_ms_stripes = {}
    #~ for stripe, wits in list(ms_stripes.items()):
        #~ st_wits = ', '.join(sorted(wits, key=lambda x: witintify(x)))
        #~ r_ms_stripes[st_wits] = stripe

    #~ keys = sorted(list(r_ms_stripes.keys()), key=lambda x: witintify(x))

    #~ for key in keys:
        #~ print('{} {}'.format(key, r_ms_stripes[key]))

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Print positive apparatus.")
    parser.add_argument('dbfile',
                        help='sqlite db filename (see populate.py)')

    args = parser.parse_args()

    print("Using database: {}".format(args.dbfile))

    main(args.dbfile)
