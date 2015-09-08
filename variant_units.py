# encoding: utf-8

import sqlite3
import sys
import re
from collections import defaultdict
import networkx
import subprocess
import csv
from itertools import chain, combinations
from populate_db import INIT, UNCL

PRIOR = "PRIOR"
POSTERIOR = "POSTERIOR"
NOREL = "NOREL"
EQUAL = "EQUAL"


class ForestError(Exception):
    pass


class ConnectivityError(Exception):
    pass


def pretty_p(x):
    """
    Turns P into a gothic 𝔓
    """
    if x.startswith('P'):
        x = u'𝔓{}'.format(x[1:])
    return x


class Coherence(object):
    """
    Class representing pre-genealogical coherence that can be extended
    to give more info.
    """
    def __init__(self, db_file, w1, variant_unit=None, pretty_p=True):
        self.conn = sqlite3.connect(db_file)
        self.cursor = self.conn.cursor()
        self.w1 = w1
        self.rows = []
        self.columns = ['W2', 'NR', 'PERC1', 'EQ', 'PASS']
        self.pretty_p = pretty_p  # normal P or gothic one...
        self.variant_unit = variant_unit
        if variant_unit:
            self.columns.extend(['READING', 'TEXT'])

        # Special formatters for the data (if required)
        self.formatters = {'PERC1': u'{:.3f}'}
        self.all_mss = [x[0] for x in self.cursor.execute('SELECT DISTINCT witness FROM attestation')]

    def _generate(self):
        """
        Generate the data
        """
        if not self.rows:
            for w2 in self.all_mss:
                if self.w1 == w2:
                    continue
                self.add_row(w2)

            self.sort()

    def add_row(self, w2):
        """
        Add a table row for witness w2
        """
        done = []
        row = {}
        while len(done) != len(self.columns):
            for col in self.columns:
                if col in done:
                    continue

                ok = self.add_item(w2, col, row)
                if ok:
                    done.append(col)

        self.rows.append(row)

    def add_item(self, w2, col, row):
        """
        Calculate the requested item (col) for w2 to the provided row dict.

        Return True if this could be done, or False if we should try again later.
        """
        col = col.replace('<', '_lt_')
        col = col.replace('>', '_gt_')
        fn = getattr(self, 'add_{}'.format(col))
        return fn(w2, row)

    def add_W2(self, w2, row):
        """
        Just add the w2 ident
        """
        if self.pretty_p:
            w2 = pretty_p(w2)
        row['W2'] = w2
        return True

    def add_NR(self, w2, row):
        """
        Rank number - this is worked out later in the sort function.
        """
        row['NR'] = None
        return True

    def add_PERC1(self, w2, row):
        """
        Percentage of agreement == coherence
        """
        if 'PASS' not in row:
            return False
        if 'EQ' not in row:
            return False
        row['PERC1'] = 100.0 * row['EQ'] / row['PASS']
        return True

    def add_EQ(self, w2, row):
        """
        Number of passages in which both witnesses agree
        """
        sql = """SELECT variant_unit AS vu, label as w1_label
                 FROM reading, attestation
                 WHERE reading.id = attestation.reading_id
                 AND attestation.witness = '{}'
                 AND EXISTS
                    (SELECT id FROM reading, attestation
                     WHERE reading.id = attestation.reading_id
                     AND variant_unit = vu
                     AND label = w1_label
                     AND attestation.witness = '{}');
              """.format(self.w1, w2)
        row['EQ'] = len(list(self.cursor.execute(sql)))
        return True

    def add_PASS(self, w2, row):
        """
        Number of passages in which both witnesses are extant
        """
        sql = """SELECT variant_unit AS vu
                 FROM reading, attestation
                 WHERE reading.id = attestation.reading_id
                 AND attestation.witness = '{}'
                 AND EXISTS
                    (SELECT id FROM reading, attestation
                     WHERE reading.id = attestation.reading_id
                     AND variant_unit = vu
                     AND attestation.witness = '{}');
              """.format(self.w1, w2)
        row['PASS'] = len(list(self.cursor.execute(sql)))
        return True

    def add_READING(self, w2, row):
        """
        Reading label (a, b, etc.) attested to by this witness in this variant
        unit.
        """
        assert self.variant_unit
        sql = """SELECT label FROM attestation, reading
                 WHERE witness = '{}'
                 AND reading.id = reading_id
                 AND variant_unit = '{}';""".format(w2, self.variant_unit)
        val = list(self.cursor.execute(sql))
        row['READING'] = val[0][0] if val else None
        return True

    def add_TEXT(self, w2, row):
        """
        Reading text attested to by this witness in this variant unit.
        """
        assert self.variant_unit
        sql = """SELECT text FROM attestation, reading
                 WHERE witness = '{}'
                 AND reading.id = reading_id
                 AND variant_unit = '{}';""".format(w2, self.variant_unit)
        val = list(self.cursor.execute(sql))
        row['TEXT'] = val[0][0] if val else None
        return True

    def sort(self):
        """
        Sort the (pre-populated) rows and supply the NR value in each case.
        """
        def sort_fn(a, b):
            if a['PERC1'] != b['PERC1']:
                return cmp(b['PERC1'], a['PERC1'])
            if a['EQ'] != b['EQ']:
                return cmp(b['EQ'], a['EQ'])
            if a['PASS'] != b['PASS']:
                return cmp(b['PASS'], a['PASS'])
            return cmp(a['W2'], b['W2'])

        self.rows.sort(sort_fn)

        rank = 0
        prev_perc = 0
        for row in self.rows:
            if row["NR"] == 0:
                # Something has already populated NR as 0 - so we set rank as
                # 0 too
                row['_RANK'] = 0
                prev_perc = 0  # reset it
                continue

            # Increment our count
            rank += 1
            if row['PERC1'] == prev_perc:
                row['NR'] = ""
                row['_RANK'] = rank
            else:
                row['NR'] = rank
                row['_RANK'] = rank
                prev_perc = row['PERC1']

    def tab_delim_table(self):
        """
        Returns a tab delimited table of the data
        """
        self._generate()

        header = ' \t '.join([r'{: ^7}'.format(col) for col in self.columns])
        lines = []
        for row in self.rows:
            bits = [self.formatters.get(col, u'{: ^7}').format(row[col])
                    for col in self.columns]
            lines.append(u' \t '.join(bits))

        return u"{}\n{}".format(header, u'\n'.join(lines))


class ReadingRelationship(object):
    """
    Class representing a reading in a specified variant unit.
    """
    def __init__(self, variant_unit, reading, cursor):
        self.variant_unit = variant_unit
        self.reading = reading
        self.cursor = cursor

    def identify_relationship(self, other_reading):
        """
        Find out how our reading is related to this other one
        """
        if self.reading == other_reading:
            return EQUAL

        #print "ID: {}, {}, {}".format(self.variant_unit, self.reading, other_reading)
        r2_ancestors = self._find_ancestor_readings(other_reading)
        if self.reading in r2_ancestors:
            return PRIOR

        r1_ancestors = self._find_ancestor_readings(self.reading)
        if other_reading in r1_ancestors:
            return POSTERIOR

        if UNCL in r1_ancestors or UNCL in r2_ancestors:
            return UNCL

        return NOREL

    def _find_ancestor_readings(self, reading):
        """
        Returns a list of ancestors, in order - possibly including UNCL
        at the end if the earliest identifiable ancestor has UNCL as parent.
        """
        sql = """SELECT parent FROM reading
                 WHERE variant_unit = \"{}\"
                 AND label = \"{}\"""".format(self.variant_unit, reading)
        self.cursor.execute(sql)
        parent = self.cursor.fetchone()[0]
        ret = [parent]
        if parent not in (INIT, UNCL):
            ret.extend(self._find_ancestor_readings(parent))
        return ret


class GenealogicalCoherence(Coherence):
    """
    Class representing genealogical coherence (potential ancestors)
    """
    def __init__(self, db_file, w1, variant_unit=None, pretty_p=True):
        super(GenealogicalCoherence, self).__init__(db_file, w1,
                                                    variant_unit, pretty_p)

        self.columns.insert(2, 'D')
        self.columns.extend(["W1<W2",  # Prior variants in W2
                             "W1>W2",  # Posterior variants in W2
                             "UNCL",
                             "NOREL"])

        # Dict of witness-reading relationships
        # {W2: {variant_unit: relationship, }, }
        self.reading_relationships = defaultdict(dict)

    def _generate(self):
        """
        Sub-classed method that hides rows that aren't potential ancestors
        """
        self._calculate_reading_relationships()
        # print self.reading_relationships
        super(GenealogicalCoherence, self)._generate()
        new_rows = []
        for row in self.rows:
            if row['W1>W2'] > row['W1<W2']:
                # W1 has more prior variants than W2 - so W2 isn't a
                # potential ancestor
                continue

            new_rows.append(row)

        self.rows = new_rows

        # Now re-sort
        self.sort()

    def _calculate_reading_relationships(self):
        """
        Populates the self.reading_relationships dictionary.

        Possible relationships are:
            PRIOR (self.w1's reading is prior to w2's)
            POSTERIOR (self.w1's reading is posterior to w2's)
            UNCL (somethere along the chain the relationship is unclear)
            NOREL (definitely no relationship betwee the readings)
            EQUAL (they're the same reading)
        """
        # Find every variant unit in which we're extant
        sql = """SELECT variant_unit, label FROM attestation, reading
                 WHERE witness = \"{}\"
                 AND attestation.reading_id = reading.id""".format(self.w1)
        for vu, label in list(self.cursor.execute(sql)):
            reading_obj = ReadingRelationship(vu, label, self.cursor)
            for w2 in self.all_mss:
                if w2 == self.w1:
                    continue
                sql = ("""SELECT label FROM attestation, reading
                          WHERE witness = \"{}\"
                          AND variant_unit = \"{}\"
                          AND attestation.reading_id = reading.id"""
                       .format(w2, vu))
                self.cursor.execute(sql.format(w2))
                row = self.cursor.fetchone()
                if row is None:
                    # lacuna
                    continue
                w2_label = row[0]
                rel = reading_obj.identify_relationship(w2_label)
                self.reading_relationships[w2][vu] = rel

    def add_D(self, w2, row):
        """
        Direction - this is used in the same way as the CBGM's genealogical
        queries program. So, it shows '-' for no direction - and basically
        nothing else.
        """
        if 'W1<W2' not in row:
            return False
        if 'W1>W2' not in row:
            return False

        if row['W1<W2'] == row['W1>W2']:
            row['D'] = '-'  # no direction
            row['NR'] = 0  # so rank 0
        else:
            row['D'] = ''

        return True

    def add_W1_lt_W2(self, w2, row):
        """
        How many times W2 has prior variants to W1
        """
        row['W1<W2'] = len([x for x in self.reading_relationships[w2].values()
                            if x == POSTERIOR])
        return True

    def add_W1_gt_W2(self, w2, row):
        """
        How many times W2 has posterior variants to W1
        """
        row['W1>W2'] = len([x for x in self.reading_relationships[w2].values()
                            if x == PRIOR])
        return True

    def add_UNCL(self, w2, row):
        """
        Count how many passages are unclear
        """
        row['UNCL'] = len([x for x in self.reading_relationships[w2].values()
                           if x == UNCL])

        return True

    def add_NOREL(self, w2, row):
        """
        Count in how many passages W2's reading has no relation to W1's reading
        """
        if 'W1<W2' not in row:
            return False
        if 'W1>W2' not in row:
            return False
        if 'UNCL' not in row:
            return False
        if 'PASS' not in row:
            return False
        if 'EQ' not in row:
            return False
        row['NOREL'] = (row['PASS'] -
                        row['EQ'] -
                        row['UNCL'] -
                        row['W1>W2'] -
                        row['W1<W2'])
        # Double check all the logic:
        norel_p = [x for x, y in self.reading_relationships[w2].items()
                   if y == NOREL]
        assert row['NOREL'] == len(norel_p), (
            w2,
            row['NOREL'],
            row['PASS'],
            row['EQ'],
            row['UNCL'],
            row['W1>W2'],
            row['W1<W2'],
            self.reading_relationships[w2],
            len(self.reading_relationships[w2]),
            norel_p)
        return True

    def potential_ancestors(self):
        """
        Return a list of potential ancestors
        """
        self._generate()
        return [x['W2'] for x in self.rows
                if x['_RANK'] != 0]


def pre_gen_coherence(db_file, w1, variant_unit=None):
    """
    Show a table of pre-genealogical coherence of all witnesses compared to w1.

    If variant_unit is supplied, then two extra columns are output
    showing the reading supported by each witness.
    """
    coh = Coherence(db_file, w1, variant_unit)
    return "{}\n{}".format("Pre-genealogical coherence for W1={}".format(w1),
                           coh.tab_delim_table().encode('utf8'))


def gen_coherence(db_file, w1, variant_unit=None):
    """
    Show a table of potential ancestors of w1.

    If variant_unit is supplied, then two extra columns are output
    showing the reading supported by each witness.
    """
    coh = GenealogicalCoherence(db_file, w1, variant_unit)
    return "{}\n{}".format("Potential ancestors for W1={}".format(w1),
                           coh.tab_delim_table().encode('utf8'))


def textual_flow(db_file, variant_unit, connectivity,
                 perfect_only=False):
    """
    Create a textual flow diagram for the specified variant unit.
    """
    print "Creating textual flow diagram for {}".format(variant_unit)
    print "Setting connectivity to {}".format(connectivity)
    if perfect_only:
        print "Insisting on perfect coherence..."
    G = networkx.DiGraph()

    sql = """SELECT witness, label, parent
             FROM attestation, reading
             WHERE attestation.reading_id = reading.id
             AND reading.variant_unit = \"{}\"
             """.format(variant_unit)
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    data = list(cursor.execute(sql))
    witnesses = [x[0] for x in data]
    G.add_nodes_from(witnesses)

    rank_mapping = {}
    for w1, w1_reading, w1_parent in data:
        print "Calculating genealogical coherence for {} at {}".format(w1, variant_unit)
        coh = GenealogicalCoherence(db_file, w1, variant_unit, False)
        coh._generate()
        best_parent = None
        for row in coh.rows:
            if row['_RANK'] > connectivity:
                # Exceeds connectivity setting
                continue
            if row['D'] == '-':
                # Not a potential ancestor (undirected genealogical coherence)
                continue
            if row['READING'] == w1_reading:
                # This matches our reading and is within the connectivity threshold - take it
                best_parent = row
                break
            if row['READING'] == w1_parent and best_parent is None:
                # Take the best row where the reading matches our parent reading
                best_parent = row

        if best_parent is None or best_parent['_RANK'] == 1:
            rank_mapping[w1] = "{} ({})".format(w1, w1_reading)
        else:
            rank_mapping[w1] = "{}/{} ({})".format(w1, best_parent['_RANK'], w1_reading)

        if not best_parent:
            if w1 == 'A':
                # That's ok...
                continue
            elif perfect_only:
                raise ForestError("Nodes with no parents - forest detected")

            print "WARNING - {} has no parents".format(w1)
            continue

        G.add_edge(best_parent['W2'], w1)

    # Relable nodes to include the rank
    networkx.relabel_nodes(G, rank_mapping, copy=False)

    print "Creating graph with {} nodes and {} edges".format(G.number_of_nodes(),
                                                             G.number_of_edges())
    networkx.write_dot(G, 'test.dot')

    output_file = "textual_flow_{}_c{}.svg".format(variant_unit.replace('/', '_'), connectivity)
    subprocess.check_call(['dot', '-Tsvg', 'test.dot'], stdout=open(output_file, 'w'))

    print "Written to {}".format(output_file)


def _post_process_dot(dotfile):
    """
    Post-process a dot file created by networkx to make it create a prettier
    local stemma.
    """
    re_node = re.compile("[^ ]+;")
    re_edge = re.compile("[^ ]+ -> [^ ]+;")

    output = []
    with open(dotfile) as df:
        for line in df:
            if re_node.match(line.strip()):
                line = line.replace(';', ' [shape=plaintext; fontsize=12; height=0.4; width=0.4; fixedsize=true];')
            elif re_edge.match(line.strip()):
                line = line.replace(';', ' [arrowsize=0.5];')
            output.append(line)

    with open(dotfile, 'w') as w:
        w.write(''.join(output))


def local_stemma(db_file, variant_unit):
    """
    Create a local stemma for the specified variant unit.
    """
    output_file = "{}.svg".format(variant_unit.replace('/', '_'))

    G = networkx.DiGraph()

    sql = """SELECT label, parent
             FROM reading
             WHERE variant_unit = \"{}\"
             """.format(variant_unit)
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    data = list(cursor.execute(sql))
    labels = [x[0] for x in data]

    G.add_nodes_from(labels)

    for label, parent in data:
        if parent == INIT:
            # We don't show a separate blob for this
            pass
        elif parent and parent != UNCL:
            G.add_edge(parent, label)
        else:
            print "WANRNING - {} has no parents".format(label)
            continue

    print "Creating graph with {} nodes and {} edges".format(G.number_of_nodes(),
                                                             G.number_of_edges())
    networkx.write_dot(G, '.tmp.dot')
    _post_process_dot('.tmp.dot')
    subprocess.check_call(['dot', '-Tsvg', '.tmp.dot', '-o', output_file])

    print "Written diagram to {}".format(output_file)

    all_mss = set([x[0] for x in cursor.execute('SELECT DISTINCT witness FROM attestation WHERE witness != "A"')])

    sql = """SELECT label, text, GROUP_CONCAT(witness)
             FROM reading, attestation
             WHERE variant_unit = \"{}\"
             AND reading.id = attestation.reading_id
             GROUP BY label
             ORDER BY label ASC
             """.format(variant_unit)

    table = ["label\ttext\twitnesses"]
    extant = set()
    for label, text, witnesses in cursor.execute(sql):
        # Ignore 'A' for local stemmata
        wits = [x for x in witnesses.split(',') if x != 'A']
        extant = extant | set(wits)
        wits = sort_mss(wits)
        wits = ', '.join(wits)
        table.append(u"{}\t{}\t{}".format(label, text, wits.replace(u'P', u'𝔓')))

    if extant != all_mss:
        wits = sort_mss(list(all_mss - extant))
        wits = ', '.join(wits)
        table.append(u"\tlac\t{}".format(wits.replace(u'P', u'𝔓')))

    return ('\n'.join(table))


def sort_mss(ms_list):
    """
    Return a sorted list of manuscripts - A first, then Papyri, then majuscules
    in order.
    """
    def witintify(x):
        # return an inte representing this witness
        if x.startswith('0'):
            return 20000 + int(re.search('([0-9]+)', x).group(1))
        elif x.startswith('P'):
            return 10000 + int(re.search('([0-9]+)', x).group(1))
        elif x == 'A':
            return 1
        else:
            raise ValueError("What? {}".format(x))

    return sorted(ms_list, key=lambda x: witintify(x))


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


def sorted_vus(cursor, sql=None):
    """
    Return a full list of variant units, properly sorted.
    """
    def numify(vu):
        a, b = vu.split('/')
        if '-' in b:
            bits = [int(x) for x in b.split('-')]
            b = float("{}.{}".format(*bits))
        else:
            b = int(b)
        a = int(a)
        return [a, b]

    if sql is None:
        sql = 'SELECT DISTINCT variant_unit FROM reading'

    return sorted([x[0] for x in cursor.execute(sql)],
                  key=lambda s: numify(s))


def status():
    """
    Show useful status info about variant units
    """
    vus = sorted_vus(cursor)
    print "All variant units ({}): ".format(len(vus)) + ', '.join(vus)
    print

    n_uncl = 0
    for vu in vus:
        sql = 'SELECT COUNT(parent) FROM reading WHERE variant_unit = "{}" AND parent = "UNCL"'.format(vu)
        cursor.execute(sql)
        uncls = int(cursor.fetchone()[0])
        if uncls:
            print "{} is unresolved ({} unclear parents)".format(vu, uncls)
            n_uncl += 1

    print "\nThere are {} unresolved variant units".format(n_uncl)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ed's CBGM implementation.")
    parser.add_argument('-f', '--db-file',
                        required=True, help='sqlite db filename (see populate.py)')
    parser.add_argument('-l', '--local-stemma', default=False, action='store_true',
                        help='print a table for a local stemma and write an svg file (requires -v)')
    parser.add_argument('-p', '--pre-genealogical-coherence', action='store_true',
                        default=False, help='show pre-genealogical coherence data (requires -w)')
    parser.add_argument('-g', '--potential-ancestors', action='store_true',
                        default=False, help='show potential ancestors (requires -w)')
    parser.add_argument('-t', '--textual-flow', default=False, action='store_true',
                        help='write a textual flow diagram. This requires -v (which can be "all")')
    parser.add_argument('-a', '--combinations-of-ancestors', action='store_true',
                        default=False, help='show combinations of ancestors (requires -w)'),
    parser.add_argument('-m', '--max-comb-len', default=999, metavar='N', type=int,
                        help='Maximum number of ancestors in a combination (-a). Default is 999.')
    parser.add_argument('-o', '--output-file', default=None,
                        help='Output filename (e.g. a csv file for -a)')
    parser.add_argument('-c', '--connectivity', default=499, metavar='N', type=int,
                        help='Maximum allowed connectivity in a textual flow diagram')
    parser.add_argument('-w', '--witness', default=None,
                        help='W1 witness ("all" shows all in sequence)')
    parser.add_argument('-v', '--variant-unit', default=None,
                        help="Show extra data about this variant unit (e.g. 1,2-8)")
    parser.add_argument('-r', '--perfect', default=False, action="store_true",
                        help="Insist on perfect coherence in a textual flow diagram")
    parser.add_argument('-s', '--strip-spaces', default=False, action="store_true",
                        help="Strip spaces from the output, making it easier to import into a spreadsheet")
    parser.add_argument('-x', '--status', default=False, action="store_true",
                        help="Show the status of all variant units (e.g. how many are unresolved)")

    args = parser.parse_args()

    print "Using database: {}".format(args.db_file)

    action = [x for x in [args.pre_genealogical_coherence,
                          args.potential_ancestors,
                          args.local_stemma,
                          args.textual_flow,
                          args.combinations_of_ancestors,
                          args.status] if x]
    coh_fn = None
    if args.pre_genealogical_coherence:
        coh_fn = pre_gen_coherence
    elif args.potential_ancestors:
        coh_fn = gen_coherence

    try:
        assert len(action) == 1, "Must specify one of -p, -g, -l, -t, -x or -a"
        if coh_fn:
            assert args.witness, "Must specify a witness for -p or -g"
        if args.textual_flow or args.local_stemma:
            assert args.variant_unit, "Must specify a variant unit for -t or -l"
    except AssertionError as e:
        print "ERROR: ", e
        parser.print_help()
        sys.exit(1)

    conn = sqlite3.connect(args.db_file)
    cursor = conn.cursor()

    all_mss = sort_mss([x[0] for x in cursor.execute('SELECT DISTINCT witness FROM attestation')])
    if args.witness and args.witness != 'all' and args.witness not in all_mss:
        print "Can't find witness: {}".format(args.witness)
        sys.exit(2)
    if args.witness == 'all':
        do_mss = all_mss
    else:
        do_mss = [args.witness]

    all_vus = sorted_vus(cursor)
    if args.variant_unit and args.variant_unit != 'all' and args.variant_unit not in all_vus:
        print "Can't find variant unit: {}".format(args.variant_unit)
        sys.exit(3)
    if args.variant_unit == 'all':
        do_vus = all_vus
    else:
        do_vus = [args.variant_unit]

    if args.status:
        status()
        sys.exit(0)

    # Now loop over all requested witnesses
    for witness in do_mss:
        if args.combinations_of_ancestors:
            combinations_of_ancestors(args.db_file, witness, args.max_comb_len,
                                      args.output_file)
            continue

        # Loop over all requested variant units
        for vu in do_vus:
            output = ''
            if coh_fn:
                # Call our coherence function
                output += coh_fn(args.db_file, witness, vu)
                output += '\n\n\n'

            elif args.local_stemma:
                output += local_stemma(args.db_file, vu)

            elif args.textual_flow:
                textual_flow(args.db_file, vu, args.connectivity, args.perfect)
                print "Written {}".format(output)

            if args.strip_spaces:
                output = output.replace(' ', '')

            print output
