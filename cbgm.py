#!/usr/bin/env python
# encoding: utf-8

import sqlite3
import sys
import logging
import time
import os
from .lib.local_stemma import local_stemma
from .lib.shared import sort_mss, sorted_vus
from .lib.textual_flow import textual_flow
from .lib.combinations_of_ancestors import combinations_of_ancestors, combanc_for_all_witnesses_mpi
from .lib.genealogical_coherence import gen_coherence
from .lib.pre_genealogical_coherence import pre_gen_coherence
from .lib.global_stemma import global_stemma, optimal_substemma
from .lib.nexus import nexus
from .lib.compare_witnesses import compare_witness_attestations
from . import populate_db

DEFAULT_DB_FILE = '/tmp/_default_cbgm_db.db'


logger = logging.getLogger(__name__)


def status(cursor):
    """
    Show useful status info about variant units

    Also returns status in a machine-readable way:
        (number of vus, number unresolved)
    """
    vus = sorted_vus(cursor)
    logger.debug("All variant units ({}): ".format(len(vus)) + ', '.join(vus))

    n_uncl = 0
    for vu in vus:
        sql = 'SELECT COUNT(DISTINCT(label)) FROM cbgm WHERE variant_unit = ? AND parent = "UNCL"'
        cursor.execute(sql, (vu,))
        uncls = int(cursor.fetchone()[0])
        if uncls:
            logger.info("{} is unresolved ({} unclear parents)".format(vu, uncls))
            n_uncl += 1

    logger.info("There are {} unresolved variant units".format(n_uncl))

    return (len(vus), n_uncl)


def get_mss_and_vus(cursor):
    """
    Get the list of all mss and vus from the database - retrying for a while if it's busy
    """
    tries = 0
    while True:
        tries += 1
        try:
            all_mss = sort_mss([x[0] for x in cursor.execute('SELECT DISTINCT witness FROM cbgm')])
        except Exception as e:
            logger.warning("Couldn't get all_mss (%s)" % e)
            if tries > 10:
                raise
            logger.warning("Retrying...")
            time.sleep(1)
        else:
            break

    tries = 0
    while True:
        tries += 1
        try:
            all_vus = sorted_vus(cursor)
        except Exception as e:
            logger.warning("Couldn't get all_vus (%s)" % e)
            if tries > 10:
                raise
            logger.warning("Retrying...")
            time.sleep(1)
        else:
            break

    return all_mss, all_vus


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ed's CBGM implementation.")
    parser.add_argument('--verbose', action='count')
    subparsers = parser.add_subparsers(help='Main commands', dest='cmd')
    subparsers.required = True

    # Data
    data_grp = parser.add_mutually_exclusive_group(required=True)
    data_grp.add_argument('-d', '--db-file',
                          help='sqlite db filename (see populate_db.py)')
    data_grp.add_argument('-f', '--file',
                          help='File containing variant reading definitions (will use populate_db.py '
                               'internally). This is slower than -d if you\'re doing lots of calls.')

    # Coherence
    coh_parser = subparsers.add_parser('coh', help='Calculate coherence tables')
    coh_parser.add_argument('witness', default=None,
                            help='W1 witness ("all" shows all in sequence)')
    coh_parser.add_argument('-v', '--variant-unit', default=None,
                            help='Show extra data about this variant unit (e.g. 1,2-8) ("all" shows all in sequence)')
    coh_parser.add_argument('-P', '--pre-genealogical-coherence', action='store_true',
                            default=False, help='show pre-genealogical coherence data')
    coh_parser.add_argument('-G', '--genealogical-coherence', action='store_true',
                            default=False, help='show genealogical coherence data (=potential ancestors)')
    coh_parser.add_argument('--min-strength', type=int, default=None,
                        help='Minimum strength to allow for a genealogical relationship (default None = disabled)'
                             ' - this applies only to Genealogical Coherence')
    coh_parser.add_argument('-n', '--no-strip-spaces', default=False, action="store_true",
                            help="Don't strip spaces from the output (stripped is better for importing into a spreadsheet)")
    coh_parser.add_argument('--gothic', default="False", action="store_true", help="Display a gothic P for papyri")
    # NOTE: The textual flow and combination of ancestors commands (below) imply use of the coherence cache
    coh_parser.add_argument('-c', '--cache', default=False, action="store_true",
                            help="Use the coherence cache for this database (requires -d).")
    coh_parser.add_argument('-e', '--extracols', default=False, action="store_true",
                            help='Show more columns in coherence tables')

    # Textual flow
    tf_parser = subparsers.add_parser('tf', help='Generate textual flow diagram (SVG)')
    tf_parser.add_argument('variant_unit', default=None,
                            help='Show extra data about this variant unit (e.g. 1,2-8) ("all" shows all in sequence)')
    tf_parser.add_argument('--rank-in-node', default=False, action="store_true",
                           help='Show the rank in the node (old method) rather than on the edge')
    tf_parser.add_argument('--simple-label', default=False, action="store_true",
                           help='Show only the rank in the edge label, rather than also the percentage')
    tf_parser.add_argument('--hide-strength', default=False, action="store_true",
                           help='Hide the textual flow strength (old method)')
    tf_parser.add_argument('--very-weak-threshold', default=5, type=int,
                           help='Threshold for considering textual flow very weak (default 5)')
    tf_parser.add_argument('--weak-threshold', default=25, type=int,
                           help='Threshold for considering textual flow weak (default 25)')
    tf_parser.add_argument('--show-strength-values', default=False, action="store_true",
                           help='Show the strength values of textual flow (incompatible with --hide-strength')
    tf_parser.add_argument('--box-readings', default=False, action="store_true",
                           help='Draw a diagram for each reading, showing that reading in a box, '
                                'with only direct ancestors from other readings')
    tf_parser.add_argument('--min-strength', type=int, default=None,
                           help='Minimum strength to allow for a genealogical relationship (default None = disabled)')
    tf_parser.add_argument('-c', '--connectivity', default="499", metavar='N/P', type=str,
                           help='Maximum allowed connectivity in a textual flow diagram (use comma separated list to '
                                'perform multiple calculations). Each value can be an int (rank) or perc (coherence).')
    tf_parser.add_argument('-s', '--suffix', default='',
                           help='Filename suffix for generated files (before the extension)')
    tf_parser.add_argument('--perfect', default=False, action="store_true",
                           help="Insist on perfect coherence in a textual flow diagram")
    tf_parser.add_argument('--include-undirected', default=False, action="store_true",
                           help="Include undirected relationships in a textual flow diagram")

    # Combination of ancestors
    anc_parser = subparsers.add_parser('combanc', help='Generate combination of ancestors')
    anc_parser.add_argument('witness', default=None,
                            help='W1 witness ("all" shows all in sequence)')
    anc_parser.add_argument('-m', '--max-comb-len', default=-1, metavar='N', type=int,
                            help='Maximum number of ancestors in a combination (-a). Default is unlimited.')
    anc_parser.add_argument('--only-complete', default=False, action="store_true",
                            help="Don't allow incomplete combinations of ancestors")
    anc_parser.add_argument('-e', '--extracols', default=False, action="store_true",
                            help='Show more columns in combinations of ancestors')
    anc_parser.add_argument('-s', '--suffix', default='',
                            help='Filename suffix for generated files (before the extension)')

    # Local stemma
    loc_parser = subparsers.add_parser('local', help='Generate local stemma table and SVG image')
    loc_parser.add_argument('variant_unit', default=None,
                            help='Show extra data about this variant unit (e.g. 1,2-8) ("all" shows all in sequence)')
    loc_parser.add_argument('-n', '--no-strip-spaces', default=False, action="store_true",
                            help="Don't strip spaces from the output (stripped is better for importing into a spreadsheet)")
    loc_parser.add_argument('-s', '--suffix', default='',
                            help='Filename suffix for generated files (before the extension)')

    # Global stemma
    gs_parser = subparsers.add_parser('global', help='Generate global stemma (SVG)')
    gs_parser.add_argument('-s', '--suffix', default='',
                           help='Filename suffix for generated files (before the extension)')
    gs_parser.add_argument('--hide-initial-text', default=False, action="store_true",
                            help="Hide the initial text, and all links from it")

    # Optimal substemmata
    opt_parser = subparsers.add_parser('optsub', help='Generate optimal substemmata data')
    opt_parser.add_argument('witness', default=None,
                            help='W1 witness ("all" shows all in sequence)')
    opt_parser.add_argument('-s', '--suffix', default='',
                            help='Filename suffix for generated files (before the extension)')

    # Status
    status_parser = subparsers.add_parser('status', help='Show status of data (for cross-checking etc.)')

    # NEXUS file
    nexus_parser = subparsers.add_parser('nexus', help='Create a NEXUS file')
    nexus_parser.add_argument('-p', '--perc', default=0, type=int,
                              help='Percentage extant a witnesses must be to be included')
    nexus_parser.add_argument('nexus_file', help='Output filename')

    # Compare witnesses
    wit_parser = subparsers.add_parser('wit', help='Compare two witness attestations')
    wit_parser.add_argument('witness', help='A witness name', nargs=2)

    args = parser.parse_args()

    # Logging
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

    # Coherence cache check
    if args.cmd == 'coh' and args.cache and args.file:
        logger.info("Cannot specify --cache with --file")
        sys.exit(8)

    # Input data
    if args.file:
        db_file = DEFAULT_DB_FILE
        populate_db.main(args.file, db_file, force=True)
    elif args.db_file:
        db_file = args.db_file
    else:
        logger.info("Please specify one of -d or -f")
        sys.exit(3)

    logger.info("Using database: {}".format(db_file))

    # Connect to database
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # MPI rank check
    try:
        from mpi4py import MPI
        mpirank = MPI.COMM_WORLD.Get_rank()
    except Exception:
        mpirank = 0

    if mpirank == 0:
        # MPI parent or simple serial run
        cursor.execute("VACUUM;")
        cursor.execute("ANALYZE;")

    # Check database connection and get all_mss and all_vus
    all_mss, all_vus = get_mss_and_vus(cursor)

    if args.cmd in('coh', 'combanc', 'optsub'):
        # Check witness exists
        if args.witness and args.witness != 'all' and args.witness not in all_mss:
            logger.info("Can't find witness: {}".format(args.witness))
            sys.exit(4)
        if args.witness == 'all':
            do_mss = all_mss
        else:
            do_mss = [args.witness]
        assert do_mss

    if args.cmd in ('coh', 'tf', 'local'):
        if args.variant_unit and args.variant_unit != 'all' and args.variant_unit not in all_vus:
            logger.info("Can't find variant unit: {}".format(args.variant_unit))
            sys.exit(5)
        if args.variant_unit == 'all':
            do_vus = all_vus
        else:
            do_vus = [args.variant_unit]
        assert do_vus

    if args.cmd in ('optsub', 'global', 'nexus'):
        if not args.file:
            logger.info("A data file is required to create the optimal substemma, global stemma, or a nexus file ('-f')")
            sys.exit(1)

    # Do the required command
    if args.cmd == 'status':
        status(cursor)

    elif args.cmd == 'global':
        global_stemma(args.file, args.suffix, args.hide_initial_text)

    elif args.cmd == 'optsub':
        for wit in do_mss:
            optimal_substemma(args.file, wit, suffix=args.suffix)

    elif args.cmd == 'local':
        output = local_stemma(db_file, do_vus, suffix=args.suffix)
        if not args.no_strip_spaces:
            output = output.replace(' ', '')

        logger.info("Output was:\n{}" .format(output))

    elif args.cmd == 'tf':
        conn = [x for x in args.connectivity.split(',')]
        if len(conn) == 1:
            logger.info("Have you considered calculating multiple connectivity "
                        "values at once? Use a comma separated list.")
        textual_flow(db_file, variant_units=do_vus, connectivity=conn,
                     perfect_only=args.perfect, ranks_on_edges=not args.rank_in_node,
                     include_perc_in_label=not args.simple_label,
                     show_strengths=not args.hide_strength,
                     weak_strength_threshold=args.weak_threshold,
                     very_weak_strength_threshold=args.very_weak_threshold,
                     show_strength_values=args.show_strength_values, suffix=args.suffix,
                     box_readings=args.box_readings, min_strength=args.min_strength,
                     include_undirected=args.include_undirected)

    elif args.cmd == 'combanc':
        if args.witness == 'all' and 'OMPI_COMM_WORLD_SIZE' in os.environ:
            combanc_for_all_witnesses_mpi(db_file, args.max_comb_len, allow_incomplete=not args.only_complete,
                                          debug=args.extracols, suffix=args.suffix)
        else:
            for witness in do_mss:
                combinations_of_ancestors(db_file, witness, args.max_comb_len,
                                          allow_incomplete=not args.only_complete,
                                          debug=args.extracols, suffix=args.suffix)

    elif args.cmd == 'coh':
        for witness in do_mss:
            # Loop over all requested variant units
            for i, vu in enumerate(do_vus):
                logger.debug("Running for variant unit {} ({} of {})"
                             .format(vu, i + 1, len(do_vus)))
                output = ''
                if args.pre_genealogical_coherence:
                    # Call our coherence function
                    output += pre_gen_coherence(db_file, witness, vu, debug=args.extracols, use_cache=args.cache,
                                                pretty_p=args.gothic)
                    output += '\n\n\n'
                elif args.genealogical_coherence:
                    # Call our coherence function
                    output += gen_coherence(db_file, witness, vu, debug=args.extracols, use_cache=args.cache,
                                            pretty_p=args.gothic, min_strength=args.min_strength)
                    output += '\n\n\n'

                if not args.no_strip_spaces:
                    output = output.replace(' ', '')

                logger.info("Output was:\n{}" .format(output))

    elif args.cmd == 'nexus':
        nexus(args.file, args.perc, args.nexus_file)

    elif args.cmd == 'wit':
        print(compare_witness_attestations(db_file, args.witness))

    else:
        assert False, "Unexpected cmd: {}".format(args.cmd)
