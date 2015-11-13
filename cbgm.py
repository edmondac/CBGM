#!/usr/bin/env python
# encoding: utf-8

import sqlite3
import sys
from lib.local_stemma import local_stemma
from lib.shared import sort_mss, sorted_vus
from lib.textual_flow import textual_flow
from lib.combinations_of_ancestors import combinations_of_ancestors
from lib.genealogical_coherence import gen_coherence
from lib.pre_genealogical_coherence import pre_gen_coherence
from lib.global_stemma import global_stemma
import populate_db

DEFAULT_DB_FILE = '/tmp/_default_cbgm_db.db'


def status(cursor):
    """
    Show useful status info about variant units
    """
    vus = sorted_vus(cursor)
    print("All variant units ({}): ".format(len(vus)) + ', '.join(vus))
    print()

    n_uncl = 0
    for vu in vus:
        sql = 'SELECT COUNT(parent) FROM reading WHERE variant_unit = "{}" AND parent = "UNCL"'.format(vu)
        cursor.execute(sql)
        uncls = int(cursor.fetchone()[0])
        if uncls:
            print("{} is unresolved ({} unclear parents)".format(vu, uncls))
            n_uncl += 1

    print("\nThere are {} unresolved variant units".format(n_uncl))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ed's CBGM implementation.")

    # Main commands
    parser.add_argument('-L', '--local-stemma', default=False, action='store_true',
                        help='print a table for a local stemma and write an svg file')
    parser.add_argument('-P', '--pre-genealogical-coherence', action='store_true',
                        default=False, help='show pre-genealogical coherence data')
    parser.add_argument('-G', '--genealogical-coherence', action='store_true',
                        default=False, help='show genealogical coherence data (=potential ancestors)')
    parser.add_argument('-T', '--textual-flow', default=False, action='store_true',
                        help='write a textual flow diagram.')
    parser.add_argument('-A', '--combinations-of-ancestors', action='store_true',
                        default=False, help='show combinations of ancestors')
    parser.add_argument('-S', '--global-stemma', action='store_true',
                        default=False, help='draw the global stemma')
    parser.add_argument('-X', '--status', default=False, action="store_true",
                        help="Show the status of all variant units (e.g. how many are unresolved)")

    # options
    parser.add_argument('-d', '--db-file',
                        help='sqlite db filename (see populate_db.py)')
    parser.add_argument('-f', '--file',
                        help='file containing variant reading definitions (will use populate_db.py internally). This is slower than -d if you\'re doing lots of calls.')
    parser.add_argument('-m', '--max-comb-len', default=-1, metavar='N', type=int,
                        help='Maximum number of ancestors in a combination (-a). Default is unlimited.')
    parser.add_argument('--csv', default=False, action="store_true",
                        help='Write a csv file for -a rather than printing the output')
    parser.add_argument('-c', '--connectivity', default=499, metavar='N', type=int,
                        help='Maximum allowed connectivity in a textual flow diagram')
    parser.add_argument('-w', '--witness', default=None,
                        help='W1 witness ("all" shows all in sequence)')
    parser.add_argument('-v', '--variant-unit', default=None,
                        help='Show extra data about this variant unit (e.g. 1,2-8) ("all" shows all in sequence)')
    parser.add_argument('-r', '--perfect', default=False, action="store_true",
                        help="Insist on perfect coherence in a textual flow diagram")
    parser.add_argument('-s', '--strip-spaces', default=False, action="store_true",
                        help="Strip spaces from the output, making it easier to import into a spreadsheet")

    args = parser.parse_args()

    if args.file and args.db_file:
        print("Please only specify one of -d and -f")
        sys.exit(2)

    if args.file:
        db_file = DEFAULT_DB_FILE
        populate_db.main(args.file, db_file, force=True)
    elif args.db_file:
        db_file = args.db_file
    else:
        print("Please specify one of -d or -f")
        sys.exit(3)

    print("Using database: {}".format(db_file))

    action = [x for x in [args.pre_genealogical_coherence,
                          args.genealogical_coherence,
                          args.local_stemma,
                          args.textual_flow,
                          args.combinations_of_ancestors,
                          args.status,
                          args.global_stemma] if x]
    coh_fn = None
    if args.pre_genealogical_coherence:
        coh_fn = pre_gen_coherence
    elif args.genealogical_coherence:
        coh_fn = gen_coherence

    try:
        assert len(action) == 1, "Must specify one of -P, -G, -L, -T, -X, -S or -A"
        if coh_fn:
            assert args.witness, "Must specify a witness (can be all)"
        if args.textual_flow or args.local_stemma:
            assert args.variant_unit, "Must specify a variant unit (can be all)"
    except AssertionError as e:
        print("ERROR: ", e)
        parser.print_help()
        sys.exit(1)

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    all_mss = sort_mss([x[0] for x in cursor.execute('SELECT DISTINCT witness FROM attestation')])
    if args.witness and args.witness != 'all' and args.witness not in all_mss:
        print("Can't find witness: {}".format(args.witness))
        sys.exit(4)
    if args.witness == 'all':
        do_mss = all_mss
    else:
        do_mss = [args.witness]

    if args.global_stemma:
        if not args.file:
            print("A data file is required to create the global stemma ('-f')")
            sys.exit(1)
        global_stemma(args.file)
        sys.exit(0)

    all_vus = sorted_vus(cursor)
    if args.variant_unit and args.variant_unit != 'all' and args.variant_unit not in all_vus:
        print("Can't find variant unit: {}".format(args.variant_unit))
        sys.exit(5)
    if args.variant_unit == 'all':
        do_vus = all_vus
    else:
        do_vus = [args.variant_unit]

    if args.status:
        status(cursor)
        sys.exit(0)

    # Now loop over all requested witnesses
    for witness in do_mss:
        if args.combinations_of_ancestors:
            # combinations_of_ancestors(db_file, witness, args.max_comb_len,
            #                          args.csv, debug=True)
            combinations_of_ancestors(db_file, witness, args.max_comb_len,
                                      args.csv)
            continue

        # Loop over all requested variant units
        for vu in do_vus:
            output = ''
            if coh_fn:
                # Call our coherence function
                output += coh_fn(db_file, witness, vu)
                output += '\n\n\n'

            elif args.local_stemma:
                output += local_stemma(db_file, vu)

            elif args.textual_flow:
                svg = textual_flow(db_file, vu, args.connectivity, args.perfect)
                output += "See {}".format(svg)

            if args.strip_spaces:
                output = output.replace(' ', '')

            print(output)
