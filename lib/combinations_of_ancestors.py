# encoding: utf-8

import sys
import time
import csv
import os
from itertools import chain, combinations
from collections import defaultdict
from .shared import UNCL, POSTERIOR, EQUAL, pretty_p, numify, memoize
from .genealogical_coherence import GenealogicalCoherence

DELIM = "\t"


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


def combinations_of_ancestors(db_file, w1, max_comb_len, *, csv_file=False,
                              connectivity=499, allow_incomplete=True,
                              debug=False, suffix=''):
    """
    Prints a table of combinations of potential ancestors ordered by
    the number required to account for all the readings in w1.

    @param db_file: db file
    @param w1: witness
    @param max_comb_len: maximum length of combinations to check (-1 for unlimited)
    @param csv_file: output to a csv file rather than a tab-delim table
    @param connectivity: maximum rank of ancestors to allow
    @param allow_incomplete: show combinations that don't explain everything
    """
    if csv_file:
        output_file = "{}{}.csv".format(w1, suffix)
        if os.path.exists(output_file):
            print("SKIPPING {} as {} already exists".format(w1, output_file))
            return None

    # FIXME - might be good to have an argument to set a threshold of what to include
    # in the output - instead of millions of rows...

    columns = ['Vorf', 'Vorfanz', 'Stellen', 'Post', 'Fragl', 'Offen',
               'Hinweis', 'sum_rank', 'ranks']
    if debug:
        columns.extend(['vus_stellen', 'vus_post', 'vus_fragl', 'vus_offen'])
    else:
        # Just include this one
        columns.extend(['vus_post'])
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

    # First to find all potential ancestors...
    coh = GenealogicalCoherence(db_file, w1, pretty_p=False)
    pot_an = coh.potential_ancestors()

    print("Found {} potential ancestors for {}".format(len(pot_an), w1))
    n_combs = 2 ** len(pot_an)
    if n_combs > 10000 and max_comb_len == -1:
        print(("WARNING: {} combinations of ancestors detected. This table could "
               "be very large and take a long time to create.\n"
               "Consider re-running with --max-comb-len set to e.g. 1000000"
               .format(n_combs)))
        ok = input("Continue? [y/N]")
        if ok.strip().lower() != 'y':
            return False

    if n_combs > max_comb_len and max_comb_len != -1:
        print("Would create {} combinations, but limited by max-comb-len to {}"
              .format(n_combs, max_comb_len))
    else:
        print("Creating {} combinations".format(n_combs))

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

    # We need to expain our reading for each vu in my_vus - and some might
    # require multiple ancestors to explain it (e.g. c&d parent)
    # So we'll cache the combinations needed for each vu first...
    vu_map = {}
    print("Loading combinations for each variant unit...")
    for idx, (vu, reading, parent) in enumerate(my_vus):
        if parent == 'UNCL':
            continue
        vu_coh = GenealogicalCoherence(db_file, w1, vu, pretty_p=False)
        vu_combs = vu_coh.parent_combinations(reading, parent, connectivity)
        # Simplify that to just a list of tuples of witnesses
        wit_combs = [set(x[0] for x in a) for a in vu_combs]
        vu_map[vu] = (vu_combs, wit_combs)
    print("Done")

    if max_comb_len == -1:
        # Unlimited
        max_comb_len = n_combs

    powerset = chain.from_iterable(combinations(pot_an, n)
                                   for n in range(min(len(pot_an) + 1, max_comb_len + 1)))
    rows = []
    total = min(n_combs, max_comb_len)
    done = 0
    start = time.time()
    report = max(total // 10000, 1)
    best_explanations = defaultdict(int)  # for working out "Hinweis"
    ranks = {x['W2']: x['_NR'] for x in coh.rows}
    for combination in powerset:
        if done >= total:
            break
        done += 1
        if done % report == 0:
            so_far = time.time() - start
            perc = done * 100.0 / total
            rem = (so_far * 100 / perc) - so_far
            sys.stdout.write("\r{}/{} ({:.2f}%) (Time taken: {}, remaining {}) - found {}     "
                             .format(done, total, perc, time_fmt(so_far), time_fmt(rem), len(rows)))
            sys.stdout.flush()
        if not combination:
            # The empty set
            continue

        ok = True
        comb_s = set(combination)
        explanation = [None for x in my_vus]
        for idx, (vu, reading, parent) in enumerate(my_vus):
            if vu not in vu_map:
                explanation[idx] = UNCL
                continue

            vu_combs, wit_combs = vu_map[vu]
            best_gen = None
            for i, c in enumerate(wit_combs):
                if c <= comb_s:
                    # This one is catered for
                    gen = max(x[2] for x in vu_combs[i])
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
            continue

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

        rows.append(row)

    print("\nCreated {} rows".format(len(rows)))

    # Now display it
    print("\n" * 5)
    rows = sorted(rows, key=lambda x: x['Fragl'])
    rows = sorted(rows, key=lambda x: x['Offen'])
    rows = sorted(rows, key=lambda x: x['Post'], reverse=True)
    rows = sorted(rows, key=lambda x: x['Stellen'], reverse=True)

    # Calculate "Hinweis" rows
    for row in rows:
        if row['Stellen'] == best_explanations[row['Vorfanz']]:
            row['Hinweis'] = '<<'

    if csv_file:
        with open(output_file, 'w') as fd:
            c = csv.writer(fd)
            c.writerow(columns)
            for row in rows:
                c.writerow([row.get(x, '') for x in columns])
            print("See {}".format(output_file))

    else:
        header = '{: <20}{}'.format(columns[0], DELIM) + DELIM.join([col for col in columns[1:]])
        lines = []
        for row in rows:
            bits = ['{: <20}'.format(row['Vorf'])] + [str(row.get(x, '')) for x in columns[1:]]
            lines.append(DELIM.join(bits))

        print("{}\n{}\n\n".format(header, '\n'.join(lines)))
