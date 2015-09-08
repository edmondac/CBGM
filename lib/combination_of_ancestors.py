import csv
from itertools import chain, combinations
from shared import UNCL, POSTERIOR, EQUAL, pretty_p, sorted_vus
from genealogical_coherence import GenealogicalCoherence


class memoize(dict):
    """
    A memoize decorator based on:
     http://wiki.python.org/moin/PythonDecoratorLibrary#Memoize
    """
    def __init__(self, func):
        self.func = func

    def __call__(self, *args):
        return self[args]

    def __missing__(self, key):
        result = self[key] = self.func(*key)
        return result


@memoize
def get_parent_reading(witness, vu, cursor):
    """
    Find the parent reading for this witness at this vu
    """
    # Not yet explained.... could be UNCL parent
    sql = """SELECT label, parent
             FROM attestation, reading
             WHERE attestation.reading_id = reading.id
             AND reading.variant_unit = \"{}\"
             AND witness = \"{}\"
             """.format(vu, witness)
    data = list(cursor.execute(sql))
    print "Witness {} has reading '{}' at {} with parent {}".format(
        witness, data[0][0], vu, data[0][1])
    return data[0][1]


def combinations_of_ancestors(db_file, w1, max_comb_len, csv_file=None):
    """
    Prints a table of combinations of potential ancestors ordered by
    the number required to account for all the readings in w1.

    @param db_file: db file
    @param w1: witness
    @param max_comb_len: maximum length of combinations to check
    @param csv_file: output to a csv file rather than a tab-delim table (filename or None)
    """
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

    print "Found {} potential ancestors for {}".format(len(pot_an), w1)
    powerset = list(chain.from_iterable(combinations(pot_an, n)
                                        for n in range(min(len(pot_an) + 1, max_comb_len + 1))))
    if len(powerset) > 100:
        print ("WARNING: {} combinations of ancestors detected. This table will "
               "be very large. Consider re-running with --max-comb-len set to a "
               "smaller number".format(len(powerset)))
        ok = raw_input("Continue? [Y/n]")
        if ok.strip().lower() == 'n':
            return False

    sql = """SELECT variant_unit AS vu
             FROM reading, attestation
             WHERE reading.id = attestation.reading_id
             AND attestation.witness = '{}';
          """.format(w1)
    my_vus = sorted_vus(coh.cursor, sql)
    # We need to expain our reading for each vu in my_vus
    rows = []
    print "Found {} combinations".format(len(powerset))
    for combination in powerset:
        if not combination:
            # The empty set
            continue

        row = {'Vorf': ', '.join([pretty_p(x) for x in combination]).encode("utf-8"),
               'Vorfanz': len(combination)}
        explanation = [None for x in my_vus]
        for w2 in combination:
            # What does this witness explain?
            #print coh.reading_relationships[w2]
            for vu, result in coh.reading_relationships[w2].items():
                index = my_vus.index(vu)
                if result == EQUAL:
                    explanation[index] = EQUAL
                elif result == POSTERIOR and explanation[index] is None:
                    explanation[index] = POSTERIOR

        for i, result in enumerate(explanation):
            if result is None:
                parent = get_parent_reading(witness, my_vus[i], coh.cursor)
                if parent == UNCL:
                    explanation[i] = UNCL

        row['Stellen'] = len([x for x in explanation if x == EQUAL])
        row['vus_stellen'] = ', '.join([my_vus[i] for i, x in enumerate(explanation) if x == EQUAL])
        row['Post'] = len([x for x in explanation if x == POSTERIOR])
        row['vus_post'] = ', '.join([my_vus[i] for i, x in enumerate(explanation) if x == POSTERIOR])
        row['Fragl'] = len([x for x in explanation if x == UNCL])
        row['vus_fragl'] = ', '.join([my_vus[i] for i, x in enumerate(explanation) if x == UNCL])
        row['Offen'] = len([x for x in explanation if x is None])
        row['vus_offen'] = ', '.join([my_vus[i] for i, x in enumerate(explanation) if x is None])

        rows.append(row)

    # Now display it
    rows = sorted(rows, key=lambda x: x['Fragl'])
    rows = sorted(rows, key=lambda x: x['Offen'])
    rows = sorted(rows, key=lambda x: x['Post'], reverse=True)
    rows = sorted(rows, key=lambda x: x['Stellen'], reverse=True)

    if csv_file is not None:
        with open(csv_file, 'w') as fd:
            c = csv.writer(fd)
            c.writerow(columns)
            for row in rows:
                c.writerow([row.get(x, u'') for x in columns])
            print "See {}".format(csv_file)

    else:
        header = r'{: ^25} | '.format(columns[0]) + r' | '.join([r'{: ^7}'.format(col) for col in columns[1:]])
        lines = []
        for row in rows:
            bits = [r'{: ^25}'.format(row['Vorf'])] + [r'{: ^7}'.format(row.get(x)) for x in columns[1:]]
            lines.append(r' | '.join(bits))

        print "{}\n{}".format(header, '\n'.join(lines))