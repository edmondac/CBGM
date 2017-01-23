#!/usr/bin/env python
# encoding: utf-8

import sqlite3
import sys
import logging
import time
from lib.local_stemma import local_stemma
from lib.shared import sort_mss, sorted_vus
from lib.textual_flow import textual_flow
from lib.combinations_of_ancestors import combinations_of_ancestors
from lib.genealogical_coherence import gen_coherence
from lib.pre_genealogical_coherence import pre_gen_coherence
from lib.global_stemma import global_stemma, optimal_substemma
import populate_db

DEFAULT_DB_FILE = '/tmp/_default_cbgm_db.db'


logger = logging.getLogger(__name__)


def status(cursor):
    """
    Show useful status info about variant units
    """
    vus = sorted_vus(cursor)
    logger.debug("All variant units ({}): ".format(len(vus)) + ', '.join(vus))

    n_uncl = 0
    for vu in vus:
        sql = 'SELECT COUNT(DISTINCT(label)) FROM cbgm WHERE variant_unit = ? AND parent = "UNCL"'
        cursor.execute(sql, (vu, ))
        uncls = int(cursor.fetchone()[0])
        if uncls:
            logger.info("{} is unresolved ({} unclear parents)".format(vu, uncls))
            n_uncl += 1

    logger.info("\nThere are {} unresolved variant units".format(n_uncl))


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
    parser.add_argument('-O', '--optimal-substemma', action='store_true',
                        default=False, help='draw the optimal substemma for a particular witness')
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
                        help='Write a csv file for -A rather than printing the output')
    parser.add_argument('--only-complete', default=False, action="store_true",
                        help="Don't allow incomplete combinations of ancestors")
    parser.add_argument('--extracols', default=False, action="store_true",
                        help='Show more columns in combinations of ancestors')
    parser.add_argument('-c', '--connectivity', default=499, metavar='N', type=int,
                        help='Maximum allowed connectivity in a textual flow diagram')
    parser.add_argument('-s', '--suffix', default='',
                        help='Filename suffix for generated files (before the extension)')
    parser.add_argument('-w', '--witness', default=None,
                        help='W1 witness ("all" shows all in sequence)')
    parser.add_argument('-v', '--variant-unit', default=None,
                        help='Show extra data about this variant unit (e.g. 1,2-8) ("all" shows all in sequence)')
    parser.add_argument('-r', '--perfect', default=False, action="store_true",
                        help="Insist on perfect coherence in a textual flow diagram")
    parser.add_argument('-n', '--no-strip-spaces', default=False, action="store_true",
                        help="Don't strip spaces from the output (stripped is better for importing into a spreadsheet)")
    parser.add_argument('--verbose', action='count')

    args = parser.parse_args()

    h1 = logging.StreamHandler(sys.stderr)
    rootLogger = logging.getLogger()
    rootLogger.addHandler(h1)
    formatter = logging.Formatter('[%(asctime)s] [%(process)s] [%(filename)s:%(lineno)s] [%(levelname)s] %(message)s')
    h1.setFormatter(formatter)

    if args.verbose:
        rootLogger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode")
    else:
        rootLogger.setLevel(logging.INFO)
        logger.debug("Run with --verbose for debug mode")

    if args.file and args.db_file:
        logger.info("Please only specify one of -d and -f")
        sys.exit(2)

    if args.file:
        db_file = DEFAULT_DB_FILE
        populate_db.main(args.file, db_file, force=True)
    elif args.db_file:
        db_file = args.db_file
    else:
        logger.info("Please specify one of -d or -f")
        sys.exit(3)

    logger.info("Using database: {}".format(db_file))

    action = [x for x in [args.pre_genealogical_coherence,
                          args.genealogical_coherence,
                          args.local_stemma,
                          args.textual_flow,
                          args.combinations_of_ancestors,
                          args.status,
                          args.global_stemma,
                          args.optimal_substemma] if x]
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
        logger.info("ERROR: ", e)
        parser.print_help()
        sys.exit(1)

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    try:
        cursor.execute("VACUUM;")
        cursor.execute("ANALYZE;")
    except Exception:
        logger.warning("Couldn't VACUUM and ANALYZE - maybe a locked database under MPI. Assuming all is fine...")

    while True:
        try:
            all_mss = sort_mss([x[0] for x in cursor.execute('SELECT DISTINCT witness FROM cbgm')])
        except Exception as e:
            logger.warning("Couldn't get all_mss (%s) - will retry" % e)
            time.sleep(1)
        else:
            break

    while True:
        try:
            all_vus = sorted_vus(cursor)
        except Exception as e:
            logger.warning("Couldn't get all_vus (%s) - will retry" % e)
            time.sleep(1)
        else:
            break

    if args.witness and args.witness != 'all' and args.witness not in all_mss:
        logger.info("Can't find witness: {}".format(args.witness))
        sys.exit(4)
    if args.witness == 'all':
        do_mss = all_mss
    else:
        do_mss = [args.witness]

    if args.optimal_substemma:
        if not args.file:
            logger.info("A data file is required to create the global stemma ('-f')")
            sys.exit(1)
        if not do_mss:
            logger.info("A witness (can be 'all') must be specified ('-w')")
            sys.exit(1)
        for wit in do_mss:
            optimal_substemma(args.file, wit, suffix=args.suffix)
        sys.exit(0)

    if args.global_stemma:
        if not args.file:
            logger.info("A data file is required to create the global stemma ('-f')")
            sys.exit(1)
        global_stemma(args.file, suffix=args.suffix)
        sys.exit(0)

    if args.variant_unit and args.variant_unit != 'all' and args.variant_unit not in all_vus:
        logger.info("Can't find variant unit: {}".format(args.variant_unit))
        sys.exit(5)
    if args.variant_unit == 'all':
        do_vus = all_vus
    else:
        do_vus = [args.variant_unit]

    if args.status:
        status(cursor)
        sys.exit(0)

    if args.combinations_of_ancestors and not args.witness:
        logger.info("Must specify -w")
        sys.exit(1)

    if args.textual_flow:
        textual_flow(db_file, do_vus, args.connectivity, args.perfect,
                     suffix=args.suffix)

    elif args.local_stemma:
        output = local_stemma(db_file, do_vus, suffix=args.suffix)
        if not args.no_strip_spaces:
            output = output.replace(' ', '')

        logger.info("Output was:\n{}" .format(output))

    else:
        # Now loop over all requested witnesses
        for witness in do_mss:
            if args.combinations_of_ancestors:
                # combinations_of_ancestors(db_file, witness, args.max_comb_len,
                #                          args.csv, debug=True)
                combinations_of_ancestors(db_file, witness, args.max_comb_len,
                                          csv_file=args.csv,
                                          allow_incomplete=not args.only_complete,
                                          debug=args.extracols, suffix=args.suffix)
                continue

            # Loop over all requested variant units
            for i, vu in enumerate(do_vus):
                logger.debug("Running for variant unit {} ({} of {})"
                             .format(vu, i + 1, len(do_vus)))
                output = ''
                if coh_fn:
                    # Call our coherence function
                    output += coh_fn(db_file, witness, vu, debug=args.extracols)
                    output += '\n\n\n'

                if not args.no_strip_spaces:
                    output = output.replace(' ', '')

                logger.info("Output was:\n{}" .format(output))
