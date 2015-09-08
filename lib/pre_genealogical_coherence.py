import sqlite3
from shared import pretty_p


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


def pre_gen_coherence(db_file, w1, variant_unit=None):
    """
    Show a table of pre-genealogical coherence of all witnesses compared to w1.

    If variant_unit is supplied, then two extra columns are output
    showing the reading supported by each witness.
    """
    coh = Coherence(db_file, w1, variant_unit)
    return "{}\n{}".format("Pre-genealogical coherence for W1={}".format(w1),
                           coh.tab_delim_table().encode('utf8'))
