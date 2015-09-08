# encoding: utf-8

from collections import defaultdict

from shared import PRIOR, POSTERIOR, NOREL, EQUAL, INIT, UNCL
from pre_genealogical_coherence import Coherence


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


def gen_coherence(db_file, w1, variant_unit=None):
    """
    Show a table of potential ancestors of w1.

    If variant_unit is supplied, then two extra columns are output
    showing the reading supported by each witness.
    """
    coh = GenealogicalCoherence(db_file, w1, variant_unit)
    return "{}\n{}".format("Potential ancestors for W1={}".format(w1),
                           coh.tab_delim_table().encode('utf8'))
