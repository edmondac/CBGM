# encoding: utf-8

import sys
import time
import csv
import os
import logging
import sqlite3
import tempfile
import subprocess
from itertools import chain, combinations
from collections import defaultdict
from .shared import UNCL, POSTERIOR, EQUAL, pretty_p, numify, memoize
from .genealogical_coherence import GenealogicalCoherence, generate_genealogical_coherence_cache

from . import mpisupport
from builtins import int

DELIM = "\t"

logger = logging.getLogger(__name__)


# Vorf = combinations
# Vorfanz = # of ancestors
# Stellen = # of variants explained by agreement with an ancestor (sort by)
# Post = # of variants explained by posterity
# Fragl = # cases of unknown source of variant (I.e. incomplete local stemma)
# Offen = # cases not explained by this combination
# Hinweis = "<<" indicates the combination explaining the most variants in
#           the descendant compared with combinations which are equal in
#           number of ancestors.
# vus_* = my columns listing the relevant variant units
SCHEMA = ["""CREATE TABLE tmp (Vorf TEXT, Vorfanz INT, Stellen INT, Post INT, Fragl INT,
                               Offen INT, Hinweis TEXT, sum_rank INT, ranks TEXT,
                               vus_stellen TEXT, vus_post TEXT, vus_fragl TEXT, vus_offen TEXT);""",
          "CREATE INDEX fraglidx ON tmp (Fragl);",
          "CREATE INDEX offenidx ON tmp (Offen);",
          "CREATE INDEX postidx ON tmp (Post);",
          "CREATE INDEX stellenidx ON tmp (Stellen);",
          "VACUUM;", "ANALYZE;"]


@memoize
def is_parent_reading_unclear(witness, vu, cursor):
    """
    Find the parent reading for this witness at this vu and return whether it's
    UNCL.

    @return: True for UNCL, False otherwise.
    """
    # Not yet explained.... could be UNCL parent
    sql = """SELECT label, parent
             FROM cbgm
             WHERE variant_unit = ?
             AND witness = ?"""
    data = list(cursor.execute(sql, (vu, witness)))
    print("Witness {} has reading '{}' at {} with parent {}".format(
        witness, data[0][0], vu, data[0][1]))
    return data[0][1] == UNCL


def time_fmt(secs):
    """
    Return a string representing the number of seconds, in a human readable
    unit.
    """
    if secs < 120:
        return "{}s".format(int(secs))
    if secs < 3600:
        return "{}m".format(secs // 60)
    return "{}h".format(secs // 3600)


def load_data(db_file, w1, max_comb_len):
    """
    Load the data, and return:
    coh : Genealogical Coherence object
    pot_an : list of potential ancestors of w1
    my_vus : a list of all variant units for this witness, as 3-tuples: ('B04K21V25/47', 'a', 'INIT')
    n_combs : the total number of possible combinations of these potential ancestors
    """
    # First to find all potential ancestors...
    coh = GenealogicalCoherence(db_file, w1, pretty_p=False, use_cache=True)
    pot_an = coh.potential_ancestors()

    print("Found {} potential ancestors for {}".format(len(pot_an), w1))
    n_combs = 2 ** len(pot_an)
    if n_combs > 10000 and max_comb_len == -1:
        logger.warning("{} combinations of ancestors detected. This table could "
                       "be very large and take a long time to create.\n"
                       "Consider re-running with --max-comb-len set to e.g. 1000000"
                       .format(n_combs))
    if n_combs > max_comb_len and max_comb_len != -1:
        logger.info("Would create {} combinations, but limited by max-comb-len to {}"
                       .format(n_combs, max_comb_len))
    else:
        logger.info("Creating {} combinations".format(n_combs))

    # NOTE: Limiting the number of combinations is ok because we will iterate
    # over the combinations starting with the smallest and getting bigger. So
    # there should be a limit (e.g. 100000) that means we've got all the
    # combinatios that we would ever actually consider as an optimal substemma.

    sql = """SELECT variant_unit, label, parent
             FROM cbgm
             WHERE witness = '{}';
          """.format(w1)
    my_vus = sorted([x for x in coh.cursor.execute(sql)],
                    key=lambda s: numify(s[0]))

    return coh, pot_an, my_vus, n_combs


def define_columns(debug=False):
    """
    Define the columns to use in the csv file
    """
    columns = ['Vorf', 'Vorfanz', 'Stellen', 'Post', 'Fragl', 'Offen',
               'Hinweis', 'sum_rank', 'ranks']
    if debug:
        # vus_stellen is just too much for spreadsheet programs - so ignore it.
        #columns.extend(['vus_stellen', 'vus_post', 'vus_fragl', 'vus_offen'])
        columns.extend(['vus_post', 'vus_fragl', 'vus_offen'])
    else:
        # Just include this one
        columns.extend(['vus_post'])

    return columns


def combinations_of_ancestors(db_file, w1, max_comb_len, allow_incomplete=True, debug=False, suffix=''):
    """
    Prints a table of combinations of potential ancestors ordered by
    the number required to account for all the readings in w1.

    @param db_file: db file
    @param w1: witness
    @param max_comb_len: maximum length of combinations to check (-1 for unlimited)
    @param allow_incomplete: show combinations that don't explain everything

    Always returns True - for MPI purposes.
    """
    output_file = "{}{}.csv".format(w1, suffix)
    if os.path.exists(output_file):
        logger.info("SKIPPING %s as %s already exists", w1, output_file)
        return True

    using_mpi = 'OMPI_COMM_WORLD_SIZE' in os.environ

    columns = define_columns(debug)
    coh, pot_an, my_vus, n_combs = load_data(db_file, w1, max_comb_len)

    # We need to explain our reading for each vu in my_vus - and some might
    # require multiple ancestors to explain it (e.g. c&d parent)
    # So we'll cache the combinations needed for each vu first...
    vu_map = {}

    logger.info("Loading combinations for %s for each variant unit...", w1)

    for (vu, reading, parent) in my_vus:
        if parent == 'UNCL':
            continue
        coh.set_variant_unit(vu)
        vu_combs = coh.parent_combinations(reading, parent)
        # Simplify that to just a list of tuples of witnesses
        wit_combs = [set(x.parent for x in a) for a in vu_combs]
        vu_map[vu] = (vu_combs, wit_combs)
    logger.info("Loaded combinations for %s for each variant unit...", w1)

    if max_comb_len == -1:
        # Unlimited
        max_comb_len = n_combs

    powerset = chain.from_iterable(combinations(pot_an, n)
                                   for n in range(min(len(pot_an) + 1, max_comb_len + 1)))
    total = min(n_combs, max_comb_len)
    done = 0
    start = time.time()
    if using_mpi:
        report = max(total // 100, 1)
    else:
        report = max(total // 10000, 1)
    best_explanations = defaultdict(int)  # for working out "Hinweis"
    ranks = {x['W2']: x['_NR'] for x in coh.rows}
    numrows = 0

    with tempfile.NamedTemporaryFile() as tmp_file:
        # set up a temporary SQL database - which we can use for sorting the data etc. later
        # without consuming all the RAM on the machine
        logger.info("Using temporary database %s", tmp_file.name)
        conn = sqlite3.connect(tmp_file.name)
        c = conn.cursor()
        for s in SCHEMA:
            c.execute(s)

        for combination in powerset:
            if done >= total:
                break
            done += 1
            if done % report == 0:
                so_far = time.time() - start
                perc = done * 100.0 / total
                rem = (so_far * 100 / perc) - so_far
                msg = "{}/{} ({:.2f}%) {} (Time taken: {}, remaining {}) - found {}     ".format(
                    done, total, perc, w1, time_fmt(so_far), time_fmt(rem), numrows)
                if using_mpi:
                    logger.debug(msg)
                else:
                    sys.stdout.write("\r{}".format(msg))
                    sys.stdout.flush()
            if not combination:
                # The empty set
                continue

            row = check_combination(combination, my_vus, vu_map, allow_incomplete, best_explanations, ranks)
            if row is not None:
                sql = ("INSERT INTO tmp ({}) VALUES ({})".format(
                    ', '.join(columns),
                    ', '.join('\"{}\"'.format(row.get(x, '')) for x in columns)))
                c.execute(sql)
                # csv_writer.writerow([row.get(x, '') for x in columns])
                numrows += 1

        if not using_mpi:
            print()

        logger.info("Created %s rows", numrows)
        write_csv(c, output_file, columns, best_explanations)
        logger.info("Wrote %s - HINT: look at the rows with << in Hinweis", output_file)

    return True


def check_combination(combination, my_vus, vu_map, allow_incomplete, best_explanations, ranks):
    ok = True
    comb_s = set(combination)
    explanation = [None for x in my_vus]
    for idx, (vu, _, _) in enumerate(my_vus):
        if vu not in vu_map:
            explanation[idx] = UNCL
            continue

        vu_combs, wit_combs = vu_map[vu]
        best_gen = None
        for i, c in enumerate(wit_combs):
            if c <= comb_s:
                # This one is catered for
                gen = max(x.gen for x in vu_combs[i])
                if best_gen is None or gen < best_gen:
                    best_gen = gen

        if best_gen is None and not allow_incomplete:
            # This combination doesn't work
            ok = False
            break

        rel = EQUAL
        if best_gen is None:
            # This doesn't explain everything
            rel = None
        elif best_gen == 2:
            # Direct parent
            rel = POSTERIOR
        elif best_gen > 2:
            # Too distant a relative. Ancestors in optimal substemmata
            # must read the same or the direct parent reading.
            rel = None
        explanation[idx] = rel

    if not ok:
        return None

    unexplained = len([x for x in explanation if x is None])
    ex_by_agreement = len([x for x in explanation if x == EQUAL])
    size = len(combination)
    if not unexplained:
        # Look for the best - which must explain everything
        best_explanations[size] = max(best_explanations[size], ex_by_agreement)

    row = {
        'Vorf': ', '.join([pretty_p(x) for x in combination]),
        'Vorfanz': size,
        'Stellen': ex_by_agreement,
        'vus_stellen': ', '.join([my_vus[i][0] for i, x in enumerate(explanation) if x == EQUAL]),
        'Post': len([x for x in explanation if x == POSTERIOR]),
        'vus_post': ', '.join([my_vus[i][0] for i, x in enumerate(explanation) if x == POSTERIOR]),
        'Fragl': len([x for x in explanation if x == UNCL]),
        'vus_fragl': ', '.join([my_vus[i][0] for i, x in enumerate(explanation) if x == UNCL]),
        'Offen': unexplained,
        'vus_offen': ', '.join([my_vus[i][0] for i, x in enumerate(explanation) if x is None]),
        'sum_rank': sum(ranks[x] for x in combination),
        'ranks': ", ".join(str(ranks[x]) for x in combination),
    }

    return row


def ResultIter(cursor, arraysize=1000):
    '''
    An iterator that uses fetchmany to keep memory usage down
    From http://code.activestate.com/recipes/137270-use-generators-for-fetching-large-db-record-sets/
    '''
    while True:
        results = cursor.fetchmany(arraysize)
        if not results:
            break
        for result in results:
            yield result


def write_csv(cursor, csv_file, columns, best_explanations):
    """
    Take the tmp database, and create a sorted CSV file with the Hinweis '<<' entries
    """
    # Column headers: Vorf,Vorfanz,Stellen,Post,Fragl,Offen,Hinweis,sum_rank,ranks,vus_stellen,vus_post,vus_fragl,vus_offen
    # Sort the CSV file to make the "best" combinations appear at the top - I.e. those with the most agreement
    # and then agreement by posterity, then with fewest errors, then fewest unknown sources, then fewest witnesses
    # in the combination, and finally the sum of the rank of those witnesses. This is just to help the user when
    # they get the file.
    sql = "SELECT {} FROM tmp ORDER BY Stellen DESC, Post DESC, Offen ASC, Fragl ASC, Vorfanz ASC, sum_rank ASC".format(
        ', '.join(columns))
    cursor.execute(sql)
    with open(csv_file, 'w', newline='') as fd:
        csv_obj = csv.DictWriter(fd, columns)
        csv_obj.writeheader()
        for result in ResultIter(cursor):
            row = {col: result[i] for i, col in enumerate(columns)}
            if row['Stellen'] == best_explanations[row['Vorfanz']]:
                # Add the magic "<<" entries that make these files easy to use
                row['Hinweis'] = '<<'

            csv_obj.writerow(row)


def mpi_child_wrapper(*args):
    """
    Wraps MPI child calls and executes the appropriate function.
    """
    key = args[0]
    if key == "GENCOH":
        return (key, generate_genealogical_coherence_cache(*args[1:]))
    elif key == "COMBANC":
        return (key, combinations_of_ancestors(*args[1:]))
    else:
        raise KeyError("Unknown MPI child key: {}".format(key))


class MpiHandler(mpisupport.MpiParent):
    mpi_child_timeout = 3600 * 4  # 4 hours

    def mpi_handle_result(self, args, ret):
        """
        Handle an MPI result
        @param args: original args sent to the child
        @param ret: response from the child
        """
        key = ret[0]
        if key in ("GENCOH", "COMBANC"):
            # There's nothing to do for genealogical coherence, since the point
            # is just to store it in a cache - and the child did that.
            # Likewise for combanc, the child has written out the data.
            assert ret[1] is True, ret
        else:
            raise KeyError("Unknown MPI child key: {}".format(key))


def combanc_for_all_witnesses_mpi(db_file, max_comb_len, *, allow_incomplete=True, debug=False, suffix=''):
    """
    Generate combination of ancestor info for all witnesses, using MPI.

    See combinations_of_ancestors for description of arguments.
    """
    if 'OMPI_COMM_WORLD_SIZE' not in os.environ:
        raise IOError("This must be run with MPI support (e.g. mpirun)")

    # We have been run with mpiexec
    mpi_parent = mpisupport.is_parent()

    if mpi_parent:
        mpihandler = MpiHandler()
    else:
        # MPI child
        mpisupport.mpi_child(mpi_child_wrapper)
        return "MPI child"

    # First generate genealogical coherence cache
    sql = "SELECT DISTINCT(witness) FROM cbgm"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    witnesses = [x[0] for x in list(cursor.execute(sql))]
    for w1 in witnesses:
        mpihandler.mpi_queue.put(("GENCOH", w1, db_file))

    # Wait for the queue, but leave the remote children running
    mpihandler.mpi_wait(stop=False)

    # Now generate combanc data
    if mpi_parent:
        for i, w1 in enumerate(witnesses):
            logger.debug("Queueing for witness %s (%s of %s)", w1, i + 1, len(witnesses))
            mpihandler.mpi_queue.put(("COMBANC", db_file, w1, max_comb_len, allow_incomplete, debug, suffix))
        return mpihandler.mpi_wait(stop=True)
    else:
        # MPI child - nothing to do as the children are already running
        pass
