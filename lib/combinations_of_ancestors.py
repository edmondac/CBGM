# encoding: utf-8

import sys
import time
import csv
from itertools import chain, combinations
from .shared import UNCL, POSTERIOR, EQUAL, pretty_p, sorted_vus, memoize
from .genealogical_coherence import GenealogicalCoherence


@memoize
def is_parent_reading_unclear(witness, vu, cursor):
    """
    Find the parent reading for this witness at this vu and return whether it's
    UNCL.

    @return: True for UNCL, False otherwise.
    """
    # Not yet explained.... could be UNCL parent
    sql = """SELECT label, parent
             FROM attestation, reading
             WHERE attestation.reading_id = reading.id
             AND reading.variant_unit = \"{}\"
             AND witness = \"{}\"
             """.format(vu, witness)
    data = list(cursor.execute(sql))
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


def combinations_of_ancestors(db_file, w1, max_comb_len, csv_file=None):
    """
    Prints a table of combinations of potential ancestors ordered by
    the number required to account for all the readings in w1.

    @param db_file: db file
    @param w1: witness
    @param max_comb_len: maximum length of combinations to check (-1 for unlimited)
    @param csv_file: output to a csv file rather than a tab-delim table (filename or None)
    """
    # FIXME - might be good to have an argument to set a threshold of what to include
    # in the output - instead of millions of rows...

    columns = ['Vorf', 'Vorfanz', 'Stellen', 'Post', 'Fragl', 'Offen',
               'Hinweis', 'vus_stellen', 'vus_post', 'vus_fragl', 'vus_offen']
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
    if n_combs > 100 and max_comb_len == -1:
        print(("WARNING: {} combinations of ancestors detected. This table could "
               "be very large and use a lot of RAM to create.\n"
               "Consider re-running with --max-comb-len set to e.g. 100000"
               .format(n_combs)))
        ok = input("Continue? [y/N]")
        if ok.strip().lower() != 'y':
            return False

    powerset = chain.from_iterable(combinations(pot_an, n)
                                   for n in range(min(len(pot_an) + 1, max_comb_len + 1)))

    sql = """SELECT variant_unit AS vu
             FROM reading, attestation
             WHERE reading.id = attestation.reading_id
             AND attestation.witness = '{}';
          """.format(w1)
    my_vus = sorted_vus(coh.cursor, sql)
    # We need to expain our reading for each vu in my_vus - and some might
    # require multiple ancestors to explain it (e.g. c&d parent)
    rows = []
    total = min(n_combs, max_comb_len)
    done = 0
    start = time.time()
    report = max(total // 10000, 1)
    for combination in powerset:
        if done >= total:
            break
        done += 1
        if done % report == 0:
            so_far = time.time() - start
            perc = done * 100.0 / total
            rem = (so_far * 100 / perc) - so_far
            sys.stdout.write("\r{}/{} ({:.2f}%) (Time taken: {}, remaining {})\t"
                             .format(done, total, perc, time_fmt(so_far), time_fmt(rem)))
            sys.stdout.flush()
        if not combination:
            # The empty set
            continue

        explanation = [None for x in my_vus]
        for w2 in combination:
            # What does this witness explain?
            #print coh.reading_relationships[w2]
            for vu, result in list(coh.reading_relationships[w2].items()):
                index = my_vus.index(vu)
                if result == EQUAL:
                    explanation[index] = EQUAL
                elif result == POSTERIOR and explanation[index] is None:
                    explanation[index] = POSTERIOR

        for i, result in enumerate(explanation):
            if result is None:
                if is_parent_reading_unclear(w1, my_vus[i], coh.cursor):
                    explanation[i] = UNCL

        row = {
            'Vorf': ', '.join([pretty_p(x) for x in combination]).encode("utf-8"),
            'Vorfanz': len(combination),
            'Stellen': len([x for x in explanation if x == EQUAL]),
            'vus_stellen': ', '.join([my_vus[i] for i, x in enumerate(explanation) if x == EQUAL]),
            'Post': len([x for x in explanation if x == POSTERIOR]),
            'vus_post': ', '.join([my_vus[i] for i, x in enumerate(explanation) if x == POSTERIOR]),
            'Fragl': len([x for x in explanation if x == UNCL]),
            'vus_fragl': ', '.join([my_vus[i] for i, x in enumerate(explanation) if x == UNCL]),
            'Offen': len([x for x in explanation if x is None]),
            'vus_offen': ', '.join([my_vus[i] for i, x in enumerate(explanation) if x is None]),
        }

        rows.append(row)

    # Now display it
    print("\n" * 5)
    rows = sorted(rows, key=lambda x: x['Fragl'])
    rows = sorted(rows, key=lambda x: x['Offen'])
    rows = sorted(rows, key=lambda x: x['Post'], reverse=True)
    rows = sorted(rows, key=lambda x: x['Stellen'], reverse=True)

    if csv_file is not None:
        with open(csv_file, 'w') as fd:
            c = csv.writer(fd)
            c.writerow(columns)
            for row in rows:
                c.writerow([row.get(x, '') for x in columns])
            print("See {}".format(csv_file))

    else:
        header = r'{: ^25} | '.format(columns[0]) + r' | '.join([r'{: ^7}'.format(col) for col in columns[1:]])
        lines = []
        for row in rows:
            bits = [r'{: ^25}'.format(row['Vorf'])] + [r'{: ^7}'.format(row.get(x)) for x in columns[1:]]
            lines.append(r' | '.join(bits))

        print("{}\n{}".format(header, '\n'.join(lines)))
