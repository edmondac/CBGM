# encoding: utf-8

import sqlite3
import logging
from collections import defaultdict
from .shared import pretty_p, memoize
logger = logging.getLogger(__name__)


class Coherence(object):
    """
    Class representing pre-genealogical coherence that can be extended
    to give more info.
    """
    def __init__(self, db_file, w1, variant_unit=None, *, pretty_p=True, debug=False):
        """
        @param db_file: database file
        @param w1: witness 1 name
        @param variant_unit: variant unit ref
        @param pretty_p: normal P or the gothic (pretty) one
        @param debug: show more columns for debugging
        """
        self.conn = sqlite3.connect(db_file)
        self.cursor = self.conn.cursor()
        self.w1 = w1
        self.rows = []
        self.columns = ['W2', 'NR', 'PERC1', 'EQ', 'PASS']
        self.pretty_p = pretty_p  # normal P or gothic one...
        self.debug = debug
        self._all_attestations = None

        self.variant_unit = variant_unit
        if variant_unit:
            self.columns.extend(['READING', 'TEXT'])

        # Special formatters for the data (if required)
        self.formatters = {'PERC1': '{:.3f}'}
        self.all_mss = [x[0] for x in self.cursor.execute('SELECT DISTINCT witness FROM cbgm')]

    def _generate(self):
        """
        Generate the data
        """
        logger.debug("Generating pre-genealogical coherence data")
        if not self.rows:
            for w2 in self.all_mss:
                if self.w1 == w2:
                    continue
                self.add_row(w2)

            self.sort()
        logger.debug("Generated pre-genealogical coherence data")

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
        if row['PASS']:
            row['PERC1'] = 100.0 * row['EQ'] / row['PASS']
        else:
            row['PERC1'] = 0.0
        return True

    def add_EQ(self, w2, row):
        """
        Number of passages in which both witnesses agree
        """
        sql = """SELECT COUNT(cbgm1.variant_unit)
                 FROM cbgm AS cbgm1, cbgm AS cbgm2
                 WHERE cbgm1.witness = '{}'
                 AND cbgm2.witness = '{}'
                 AND cbgm1.variant_unit = cbgm2.variant_unit
                 AND cbgm1.label = cbgm2.label;
              """.format(self.w1, w2)
        row['EQ'] = list(self.cursor.execute(sql))[0][0]
        return True

    def add_PASS(self, w2, row):
        """
        Number of passages in which both witnesses are extant
        """
        sql = """SELECT COUNT(cbgm1.variant_unit)
                 FROM cbgm AS cbgm1, cbgm AS cbgm2
                 WHERE cbgm1.witness = ?
                 AND cbgm2.witness = ?
                 AND cbgm1.variant_unit = cbgm2.variant_unit;
              """
        row['PASS'] = list(self.cursor.execute(sql, (self.w1, w2)))[0][0]
        return True

    def all_attestations(self):
        """
        All attestations - getting this piecemeal is slow, so we'll cache it
        """
        if self._all_attestations:
            return self._all_attestations

        ret = defaultdict(defaultdict)
        for row in self.cursor.execute("""SELECT witness, variant_unit, label FROM cbgm"""):
            witness, vu, label = row
            ret[witness][vu] = label

        self._all_attestations = ret

        return ret

    def get_attestation(self, witness, vu):
        """
        A cache to find out what a witness reads in a variant unit
        """
        return self.all_attestations()[witness].get(vu)

    def add_READING(self, w2, row):
        """
        Reading label (a, b, etc.) attested to by this witness in this variant
        unit.
        """
        assert self.variant_unit
        row['READING'] = self.get_attestation(w2, self.variant_unit)
        return True

    def add_TEXT(self, w2, row):
        """
        Reading text attested to by this witness in this variant unit.
        """
        assert self.variant_unit
        sql = """SELECT text FROM cbgm
                 WHERE witness = ?
                 AND variant_unit = ?;"""
        val = list(self.cursor.execute(sql, (w2, self.variant_unit)))
        row['TEXT'] = val[0][0] if val else None
        return True

    def sort(self):
        """
        Sort the (pre-populated) rows and supply the NR value in each case.
        """
        self.rows.sort(key=lambda x: (x['PERC1'], x['EQ'], x['PASS'], x['W2']),
                       reverse=True)

        rank = 0
        prev_perc = 0
        prev_rank = 0
        for row in self.rows:
            if row["NR"] == 0:
                # Something has already populated NR as 0 - so we set rank as
                # 0 too
                row['_RANK'] = 0
                row['_NR'] = 0
                continue

            # Increment our count
            rank += 1
            if row['PERC1'] == prev_perc:
                row['NR'] = ""
                row['_NR'] = prev_rank  # I.e. joint 6th will be 6 here
                row['_RANK'] = rank  # I.e. joint 6th could be 7, or 8 etc. here
            else:
                row['NR'] = rank
                row['_NR'] = rank
                row['_RANK'] = rank
                prev_perc = row['PERC1']
                prev_rank = rank

    def tab_delim_table(self):
        """
        Returns a tab delimited table of the data
        """
        self._generate()

        header = ' \t '.join([r'{: ^7}'.format(col) for col in self.columns])
        lines = []
        for row in self.rows:
            bits = []
            for col in self.columns:
                if col in self.formatters:
                    bits.append(self.formatters[col].format(row[col]))
                else:
                    bits.append(self.formatters.get(col, '{: ^7}').format(row[col] if row[col] else ''))
            lines.append(' \t '.join(bits))

        return "{}\n{}".format(header, '\n'.join(lines))


def pre_gen_coherence(db_file, w1, variant_unit=None, *, debug=False):
    """
    Show a table of pre-genealogical coherence of all witnesses compared to w1.

    If variant_unit is supplied, then two extra columns are output
    showing the reading supported by each witness.
    """
    coh = Coherence(db_file, w1, variant_unit, debug=debug)
    return "{}\n{}".format("Pre-genealogical coherence for W1={}".format(w1),
                           coh.tab_delim_table())
