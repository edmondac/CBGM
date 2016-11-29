#!/usr/bin/env python
# encoding: utf-8

import re
import sqlite3
from lib.shared import INIT, OL_PARENT


def main(db_file):
    """
    Prints out all the parts required for a positive apparatus.

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
        sql = "SELECT DISTINCT label, text, parent FROM cbgm WHERE variant_unit = ?"
        cursor.execute(sql, (unit, ))

        def sorter(x):
            if x['parent'] == INIT:
                # This will show up first...
                return '_'
            elif x['parent'] == OL_PARENT:
                # Parent reading of an overlapped unit where the initial text is lacunose
                return '_'
            else:
                return x['label']

        readings = sorted([{'label': x[0],
                            'text': x[1],
                            'parent': x[2]} for x in cursor.fetchall()],
                          key=sorter)
        print()
        print(unit)
        for reading in readings:
            sql = "SELECT witness FROM cbgm WHERE label=? and variant_unit=?"
            cursor.execute(sql, (reading['label'], unit))
            attestations = sorted([x[0] for x in cursor.fetchall()],
                                  key=lambda a: witintify(a))
            print("{} {} {}".format(reading['label'],
                                    reading['text'],
                                    ', '.join(attestations)))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Print positive apparatus.")
    parser.add_argument('dbfile',
                        help='sqlite db filename (see populate.py)')

    args = parser.parse_args()

    print("Using database: {}".format(args.dbfile))

    main(args.dbfile)
