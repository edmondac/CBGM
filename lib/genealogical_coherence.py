# encoding: utf-8

from collections import defaultdict
from itertools import product, chain
from toposort import toposort

from .shared import PRIOR, POSTERIOR, NOREL, EQUAL, INIT, OL_PARENT, UNCL, LAC, memoize
from .pre_genealogical_coherence import Coherence


class TooManyAborts(Exception):
    pass


class CyclicDependency(Exception):
    pass


class ReadingRelationship(object):
    """
    Class representing a reading in a specified variant unit.
    """
    def __init__(self, variant_unit, reading, cursor):
        self.variant_unit = variant_unit
        self.reading = reading
        self.cursor = cursor
        self._recursion_history = []
        self._abort_count = 0

    def identify_relationship(self, other_reading):
        """
        Find out how our reading is related to this other one
        """
        if self.reading == other_reading:
            return EQUAL

        # Even though some readings have multiple parents (c&d), the question
        # here is not 'does X explain Y completely?' but instead it's 'which of
        # X and Y is PRIOR?' Local stemma are not allowed loops, so we can
        # always answer that question.

        r2_ancestor = self.get_parent_reading(other_reading)
        if self.reading == r2_ancestor:
            return PRIOR

        r1_ancestor = self.get_parent_reading(self.reading)
        if other_reading == r1_ancestor:
            return POSTERIOR

        if UNCL == r1_ancestor or UNCL == r2_ancestor:
            return UNCL

        return NOREL

    def get_parent_reading(self, reading):
        """
        Get the parent reading for this reading
        """
        sql = """SELECT parent FROM reading
                 WHERE variant_unit = \"{}\"
                 AND label = \"{}\"""".format(self.variant_unit, reading)
        self.cursor.execute(sql)
        return self.cursor.fetchone()[0]


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
        self._already_generated = False
        self._parent_search = set()

    def _generate(self):
        """
        Sub-classed method that hides rows that aren't potential ancestors
        """
        if self._already_generated:
            return

        # Check for bad data
        data = defaultdict(set)
        sql = """SELECT label, parent FROM reading
                 WHERE variant_unit = \"{}\"
                 """.format(self.variant_unit)
        self.cursor.execute(sql)
        for row in self.cursor:
            data[row[0]].add(row[1])
        try:
            topo = list(toposort(data))
        except ValueError:
            # There's a cycle in our data...
            raise CyclicDependency

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

        self._already_generated = True

    @memoize
    def all_attestations(self):
        """
        All attestations - getting this piecemeal is slow, so we'll cache it
        """
        ret = defaultdict(defaultdict)
        for row in self.cursor.execute("""SELECT witness, variant_unit, label
                                          FROM attestation, reading
                                          WHERE attestation.reading_id = reading.id"""):
            witness, vu, label = row
            ret[witness][vu] = label

        return ret

    def get_attestation(self, witness, vu):
        """
        A cache to find out what a witness reads in a variant unit
        """
        return self.all_attestations()[witness].get(vu)

    def _calculate_reading_relationships(self):
        """
        Populates the self.reading_relationships dictionary.

        Possible relationships are:
            PRIOR (self.w1's reading is directly prior to w2's)
            POSTERIOR (self.w1's reading is directly posterior to w2's)
            UNCL (one or other of w1 and w2 has an unclear parent)
            NOREL (no direct relationship between the readings)
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
                attestation = self.get_attestation(w2, vu)
                if attestation is None:
                    # Nothing for this witness at this place
                    continue
                w2_label = attestation
                if w2_label == LAC:
                    # lacuna
                    continue
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
        row['W1<W2'] = len([x for x in list(self.reading_relationships[w2].values())
                            if x == POSTERIOR])
        return True

    def add_W1_gt_W2(self, w2, row):
        """
        How many times W2 has posterior variants to W1
        """
        row['W1>W2'] = len([x for x in list(self.reading_relationships[w2].values())
                            if x == PRIOR])
        return True

    def add_UNCL(self, w2, row):
        """
        Count how many passages are unclear
        """
        row['UNCL'] = len([x for x in list(self.reading_relationships[w2].values())
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
        norel_p = [x for x, y in list(self.reading_relationships[w2].items())
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
                if x['_NR'] != 0]

    def parent_combinations(self, reading, parent_reading, max_rank=499, my_gen=1):
        """
        Return a list of possible parent combinations that explain this reading.

        If the parent_reading is of length 3 (e.g. c&d&e) then the combinations
        will be length 3 or less.

        Returns a list of lists, e.g.:
            [
             # 05 explains this reading by itself
             [('05' = witness, 4 = rank, 1 = generation)],

             # 03 and P75 are both required to explain this reading and both
             # are generation 2 (e.g. attest a parent reading)
             [('03', 3, 2), ('P75', 6, 2)],

             # A explains this reading by itself but it is generation 3 - in
             # other words all witnesses attesting our parent readings all
             # have A as their parent (one with rank 6 and one with rank 4)
             [('A', 6, 3), ('A', 4, 3)],
             ...
             ]
        """
        self._generate()
        if my_gen == 1:
            # top level
            self._parent_search = set()

        ret = []
        # Things that explain it by themselves:
        for row in self.rows:
            # Check the real rank (_NR) - so joint 6th => 6. _RANK here could be
            # 7, 8, 9 etc. for joint 6th.
            if row['_NR'] > max_rank:
                # Exceeds connectivity setting
                continue
            elif row['D'] == '-':
                # Not a potential ancestor (undirected genealogical coherence)
                continue
            elif row['READING'] == reading:
                # This matches our reading and is within the connectivity threshold - take it
                ret.append([(row['W2'], row['_NR'], my_gen)])

        if parent_reading in (INIT, OL_PARENT, UNCL):
            # No parents - nothing further to do
            return ret

        # Now the parent reading
        partial_explanations = []
        bits = parent_reading.split('&')
        for partial_parent in bits:
            if partial_parent in self._parent_search:
                # Already been here - must be looping...
                continue

            self._parent_search.add(partial_parent)

            if partial_parent == INIT:
                # Simple - who reads INIT?
                partial_explanations.append(
                    self.parent_combinations(INIT, None, max_rank, my_gen + 1))
                continue
            if partial_parent == OL_PARENT:
                # Simple - who reads OL_PARENT?
                partial_explanations.append(
                    self.parent_combinations(OL_PARENT, None, max_rank, my_gen + 1))
                continue

            # We need to recurse, and find out what combinations explain our
            # (partial) parent.
            reading_obj = ReadingRelationship(self.variant_unit,
                                              partial_parent,
                                              self.cursor)

            expl = self.parent_combinations(
                partial_parent,
                reading_obj.get_parent_reading(partial_parent),
                max_rank,
                my_gen + 1)

            partial_explanations.append(expl)

        if not partial_explanations:
            # We couldn't find anything
            return []

        if len(partial_explanations) == 1:
            # We've got a single parent - simple
            ret.extend(partial_explanations[0])
            return ret

        else:
            # We now combine the lists in such a way as to get the same structure
            # as above but now with (potentially) multiple tuples in the inner lists.
            prod = product(*partial_explanations)
            combined = list(list(set(chain(*x))) for x in prod)
            return combined


def gen_coherence(db_file, w1, variant_unit=None):
    """
    Show a table of potential ancestors of w1.

    If variant_unit is supplied, then two extra columns are output
    showing the reading supported by each witness.
    """
    coh = GenealogicalCoherence(db_file, w1, variant_unit)
    return "{}\n{}".format("Potential ancestors for W1={}".format(w1),
                           coh.tab_delim_table())
