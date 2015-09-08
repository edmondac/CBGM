#!/usr/bin/env python
# encoding: utf-8
# Script to populate a sqlite database given a suitable input file


import sqlite3
import os
import importlib
from lib.shared import INIT


class AllBut(object):
    def __init__(self, *args):
        """
        Class to return a set of all manuscripts minus the ones specified.
        """
        self.args = args

    def calc(self, all_mss):
        """
        Return a set of all manuscripts minus the ones specified.

        @param all_mss: The full list of available manuscripts

        Also, 'A' is not included as that's added specially in the __init__ of
        class Reading.
        """
        for x in self.args:
            assert x in all_mss, (x, all_mss)
        return all_mss - set(self.args) - set(['A'])


class Reading(object):
    def __init__(self, label, greek, ms_support, parent):
        self.lacuna = False
        self.label = label
        self.greek = greek
        self._ms_support = ms_support
        self.ms_support = False
        self.parent = parent

    def calc_mss_support(self, all_mss):
        """
        Calculate manuscript support based on the list of all mss passed in
        """
        if self._ms_support is not None:
            if hasattr(self._ms_support, 'calc'):
                self._ms_support = self._ms_support.calc(all_mss)
            self.ms_support = set(self._ms_support)
            for x in self.ms_support:
                if x != 'A':
                    assert x in all_mss, (x, all_mss)
        else:
            self.ms_support = None

        if self.parent == INIT:
            self.ms_support.add('A')

    def __repr__(self):
        return "<Reading: label:{}, parent:{}>".format(self.label, self.parent)


class LacunaReading(Reading):
    def __init__(self, ms_support):
        self.ms_support = set(ms_support)
        self.lacuna = True
        self.label = 'lac'
        self.parent = None


def parse_input_file(filename):
    """
    Import and parse the input file.
    """
    # We need to add . to the path, so we can import the specified python file
    # even if this script has been called by a full path.
    import sys
    sys.path.append(".")

    if filename.endswith('.py'):
        filename = filename[:-3]
    mod = importlib.import_module(filename)
    assert 'A' not in mod.all_mss
    return mod.struct, mod.all_mss


SCHEMA = [
    "CREATE TABLE reading (id PRIMARY KEY, variant_unit, label, text, parent);",
    "CREATE TABLE attestation (reading_id, witness, FOREIGN KEY(reading_id) REFERENCES reading(id));"]


def populate(data, all_mss, db_file, force=False):
    """
    Populate a database file based on the readings above
    """
    print "Will populate {}".format(db_file)

    if os.path.exists(db_file):
        if force:
            os.unlink(db_file)
        else:
            raise ValueError("File {} already exists".format(db_file))

    conn = sqlite3.connect(db_file)
    c = conn.cursor()

    for s in SCHEMA:
        c.execute(s)

    reading_id = 0
    vu_count = 0
    for verse in data:
        for vu in data[verse]:
            vu_count += 1
            all_wits_found = set()
            for reading in data[verse][vu]:
                if not reading.lacuna:
                    reading.calc_mss_support(all_mss)

                assert not reading.ms_support & all_wits_found, (
                    reading.ms_support & all_wits_found,
                    verse, vu)

                all_wits_found = all_wits_found | reading.ms_support

                if reading.lacuna:
                    # Ignore these as the witness can't support any reading
                    continue

                reading_id += 1
                sql = (u"""INSERT INTO reading
                              (id, variant_unit, label, text, parent)
                          VALUES ({}, \"{}/{}\", \"{}\", \"{}\", \"{}\")"""
                       .format(reading_id,
                               verse,
                               vu,
                               reading.label,
                               reading.greek,
                               reading.parent))

                c.execute(sql)
                for ms in reading.ms_support:
                    sql = """INSERT INTO attestation
                              (reading_id, witness)
                             VALUES ({}, \"{}\")""".format(reading_id, ms)
                    c.execute(sql)

            if all_mss - all_wits_found:
                print "-------" * 10
                print "WARNING " * 10
                print "Witnesses don't match for vu {}/{}".format(verse, vu)
                print "Don't forget to include a LacunaReading if the witness isn't extant"
                print "Missing witnesses: ", all_mss - all_wits_found
                print "-------" * 10

    conn.commit()
    conn.close()
    print "Wrote {} variant units".format(vu_count)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Populate sqlite database")
    parser.add_argument('inputfile', help='file containing variant reading definitions')
    parser.add_argument('dbfile', help='filename for new sqlite db')
    parser.add_argument('--force', default=False, action='store_true',
                        help='force mode - overwrite any files that get in the way')

    args = parser.parse_args()
    struct, all_mss = parse_input_file(args.inputfile)
    populate(struct, all_mss, args.dbfile, force=args.force)
