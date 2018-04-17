#!/usr/bin/env python
# encoding: utf-8
# Script to populate a sqlite database given a suitable input file

import importlib.util
import sqlite3
import os
import importlib
from .shared import INIT, LAC
import logging

logger = logging.getLogger(__name__)


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

        if label in parent.split('&'):
            logger.warning("Reading {} has parent {} - causing a loop. Greek: {}, MSS: {}"
                           .format(label, parent, greek, ms_support))

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
        self._ms_support = ms_support
        self.ms_support = False
        self.lacuna = True
        self.label = LAC
        self.parent = None


def parse_input_file(filename):
    """
    Import and parse the input file.
    """
    modname = os.path.splitext(os.path.basename(filename))[0]
    spec = importlib.util.spec_from_file_location(modname, filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert 'A' not in mod.all_mss
    assert type(mod.all_mss) == set
    return mod.struct, mod.all_mss


# Old normalized schema (fast inserts and updates, slow selects):
# SCHEMA = [
    # "CREATE TABLE reading (id PRIMARY KEY, variant_unit, label, text, parent);",
    # "CREATE TABLE attestation (reading_id, witness, FOREIGN KEY(reading_id) REFERENCES reading(id));"]
# New de-normalized schema (slow inserts and updates, fast selects):
SCHEMA = ["CREATE TABLE cbgm (witness, variant_unit, label, text, parent);",
          "CREATE INDEX varidx ON cbgm (variant_unit);",
          "CREATE INDEX witidx ON cbgm (witness);",
          "CREATE INDEX labidx ON cbgm (label);",
          "CREATE INDEX paridx ON cbgm (parent);",
          "VACUUM;", "ANALYZE;"]


def create_database(data, all_mss, db_file, force=False):
    """
    Populate a database file based on the readings above
    """
    logger.info("Will populate {}".format(db_file))

    if os.path.exists(db_file):
        if force:
            os.unlink(db_file)
        else:
            raise ValueError("File {} already exists".format(db_file))

    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    for s in SCHEMA:
        c.execute(s)

    vu_count = 0
    for verse in data:
        for vu in data[verse]:
            vu_count += 1
            all_wits_found = set()
            for reading in data[verse][vu]:
                reading.calc_mss_support(all_mss)

                if reading.ms_support & all_wits_found:
                    raise IOError("HELP - I've already seen these witnesses for {}/{}: {}"
                                  .format(verse, vu, reading.ms_support & all_wits_found))

                all_wits_found = all_wits_found | reading.ms_support

                if reading.lacuna:
                    # Ignore these as the witness can't support any reading
                    continue

                for ms in reading.ms_support:
                    sql = ("""INSERT INTO cbgm
                                  (witness, variant_unit, label, text, parent)
                              VALUES (\"{}\", \"{}/{}\", \"{}\", \"{}\", \"{}\")"""
                           .format(ms,
                                   verse,
                                   vu,
                                   reading.label,
                                   reading.greek,
                                   reading.parent))
                    c.execute(sql)

            if all_mss - all_wits_found:
                logger.warning("-------" * 10)
                logger.warning("WARNING " * 10)
                logger.warning("Witnesses don't match for vu {}/{}".format(verse, vu))
                logger.warning("Don't forget to include a LacunaReading if the witness isn't extant")
                logger.warning("Missing witnesses: ", all_mss - all_wits_found)
                logger.warning("-------" * 10)

    conn.commit()
    conn.close()
    logger.info("Wrote {} variant units".format(vu_count))


def populate(in_f, out_f, force):
    """
    Convert a CBGM python data file into a SQLite database.

    @param in_f: struct filename
    @param out_f: db output filename
    @param force: overwrite things if they're in the way
    """
    struct, all_mss = parse_input_file(in_f)
    return create_database(struct, all_mss, out_f, force=force)



