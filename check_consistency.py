# Check consistency of all local stemmata (where there are no UNCL relationships).


import tempfile
import shutil
import os
import sqlite3
import webbrowser

from lib.shared import sorted_vus
from lib.textual_flow import textual_flow
from populate_db import parse_input_file, populate
import populate_db
from lib.shared import UNCL
from lib.mpisupport import MpiParent, mpi_child, is_parent
from lib.genealogical_coherence import CyclicDependency


def has_unclear(vu, cursor):
    """
    Check if the given variant unit has any UNCL relationships
    """
    sql = """SELECT parent FROM cbgm
             WHERE variant_unit = ?
             AND parent = ?"""
    cursor.execute(sql, (vu, UNCL))
    return bool(cursor.fetchall())


class CheckConsistency(MpiParent):
    def __init__(self, inputfile, connectivity):
        super().mpi_run()
        self.results = {}
        self.connectivity = connectivity

        self.working_dir = tempfile.mkdtemp()
        shutil.copyfile(inputfile, os.path.join(self.working_dir, inputfile))
        os.chdir(self.working_dir)

        struct, all_mss = parse_input_file(inputfile)

        # Make our own temporary db
        with tempfile.NamedTemporaryFile() as db:
            populate_db.main(inputfile, db.name, force=True)
            conn = sqlite3.connect(db.name)
            cursor = conn.cursor()
            self.vus = list(sorted_vus(cursor))

            for vu in self.vus:
                if has_unclear(vu, cursor):
                    self.results[vu] = "UNCL relationships detected"
                    continue

                self.mpi_queue.put((struct, all_mss, vu, connectivity))

        self.mpi_wait()
        self.collate_results()

    def collate_results(self):
        """
        Write the HTML file
        """
        html = """<html><h1>Consistency: Textual flow diagrams</h1>
                    <p> for all variant units with complete local stemmata (I.e. no UNCL relationships).</p>
                    <h1> Connectivity: {}</h1>
               """.format(self.connectivity)
        for vu in self.vus:
            # collate results
            res = self.results[vu]
            if res is None:
                html += '<h2>{}</h2><p>ERROR</p><hr/>\n'.format(vu)
            elif 'svg' in res:
                html += ('<h2>{}</h2><img width="500px" src="{}"/><br/><hr/>\n'
                         .format(vu, res))
            else:
                html += '<h2>{}</h2><p>ERROR: {}</p><hr/>\n'.format(vu, res)

        html += "</html>"
        with open('index.html', 'w') as f:
            f.write(html)

        print("View the files in {}".format(self.working_dir))

        print("Opening browser...")
        webbrowser.open(os.path.join(os.path.join(self.working_dir, 'index.html')))

    def mpi_handle_result(self, args, ret):
        """
        Handle an MPI result
        @param args: original args sent to the child
        @param ret: response from the child
        """
        vu = args[2]
        if ret is None:
            # error calculating this one
            self.results[vu] = None
        else:
            # recreate the svg locally
            with open(ret['svgname'], 'wb') as f:
                f.write(ret['svgdata'])

            self.results[vu] = ret['svgname']


def child(struct, all_mss, vu, connectivity):
    """
    MPI child function
    """
    # Do this in our own temp dir
    mytemp = tempfile.mkdtemp()
    os.chdir(mytemp)

    # 1. Populate the db
    db = '_temp.db'
    populate(struct, all_mss, db)

    # 2. Make the textual flow diagram
    try:
        svg = textual_flow(db, vu, connectivity, perfect_only=False)
    except CyclicDependency:
        return None

    with open(svg, 'rb') as f:
        return {'svgname': svg, 'svgdata': f.read()}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Check consistency for all completed local stemmata by creating textual flow diagrams.")
    parser.add_argument('inputfile', help='file containing variant reading definitions')
    parser.add_argument('-c', '--connectivity', default=499, metavar='N', type=int,
                        help='Maximum allowed connectivity in a textual flow diagram')

    args = parser.parse_args()
    is_parent = is_parent()

    if is_parent:
        # parent or only process
        CheckConsistency(args.inputfile, args.connectivity)
    else:
        # child
        mpi_child(child)
