"""
Compare the attestations of two witnesses
"""

import logging
import sqlite3
from collections import namedtuple
from .genealogical_coherence import ReadingRelationship
from .shared import EQUAL, PRIOR, POSTERIOR, UNCL, NOREL

logger = logging.getLogger(__name__)

variant_unit = namedtuple('variant_unit', ('label', 'text', 'parent'))

def compare_witness_attestations(db, wits):
    return Attestations(db).compare(wits)


class Attestations(object):
    def __init__(self, db_file):
        self.conn = sqlite3.connect(db_file)
        self.cursor = self.conn.cursor()

    def compare(self, wits):
        """
        Compare the attestations of the supplied pair of witnesses, showing where they agree and what relationship
        they have where they disagree (if any).
        :param wits: list of witness names
        :return: (string) report
        """
        ret = []

        assert len(wits) == 2, wits
        w1 = wits[0]
        w2 = wits[1]

        w1_att = self._get_attestations(w1)
        w2_att = self._get_attestations(w2)

        w1_vus = set(w1_att.keys())
        w2_vus = set(w2_att.keys())

        overlap = sorted(w1_vus & w2_vus)

        ret.append("{} and {} overlap in {} variant units".format(w1, w2, len(overlap)))

        equal = 0
        w1_prior = 0
        w1_posterior = 0
        uncl = 0
        norel = 0

        for vu in overlap:
            w1_reading = w1_att[vu]
            w2_reading = w2_att[vu]
            relationship = ReadingRelationship(vu, w1_reading.label, self.cursor).identify_relationship(w2_reading.label)
            if relationship == EQUAL:
                msg = "{} and {} agree".format(w1, w2)
                equal += 1
            elif relationship == PRIOR:
                msg = "{} has a prior reading".format(w1)
                w1_prior += 1
            elif relationship == POSTERIOR:
                msg = "{} has a posterior reading".format(w1)
                w1_posterior += 1
            elif relationship == UNCL:
                msg = "{} and/or {} has an unclear relationship".format(w1, w2)
                uncl += 1
            elif relationship == NOREL:
                msg = "{} and {} are unrelated".format(w1, w2)
                norel += 1

            ret.append("> {}:\n\t{} reads {} ({})\n\t{} reads {} ({})\n\t> {}".format(
                vu, w1, w1_reading.text, w1_reading.label, w2, w2_reading.text, w2_reading.label, msg))

        ret.append("")
        ret.append("Summary:")
        ret.append(" * {} and {} agree in {} variant units".format(w1, w2, equal))
        ret.append(" * {} has a prior reading in {} variant units".format(w1, w1_prior))
        ret.append(" * {} has a posterior reading in {} variant units".format(w1, w1_posterior))
        ret.append(" * {} and/or {} has an unclear relationship in {} variant units".format(w1, w2, uncl))
        ret.append(" * {} and {} are unrelated in {} variant units".format(w1, w2, norel))
        return '\n'.join(ret)

    def _get_attestations(self, wit):
        """
        Attestations for a witness
        """
        logger.debug("Loading attestations for %s", wit)
        ret = {}
        rows = self.cursor.execute("SELECT variant_unit, label, text, parent FROM cbgm WHERE witness=?", (wit, ))
        for (vu, label, text, parent) in rows:
            ret[vu] = variant_unit(label, text, parent)
        return ret
