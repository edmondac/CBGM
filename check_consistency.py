# Check consistency of all local stemmata (where there are no UNCL relationships).


import tempfile
import shutil
import os
import sqlite3
import webbrowser

from lib.shared import sorted_vus
from lib.textual_flow import textual_flow
import populate_db


def main(inputfile, connectivity):
    working_dir = tempfile.mkdtemp()
    shutil.copyfile(inputfile, os.path.join(working_dir, inputfile))
    os.chdir(working_dir)

    html = "<html>\n"

    with tempfile.NamedTemporaryFile() as db:
        populate_db.main(inputfile, db.name, force=True)
        conn = sqlite3.connect(db.name)
        cursor = conn.cursor()
        vus = list(sorted_vus(cursor))
        for vu in vus:
            # FIXME - check for UNCL in this vu
            svg = textual_flow(db.name, vu, connectivity, perfect_only=False)
            if svg is not None and 'svg' in svg:
                html += ('<h2>{}</h2><img width="500px" src="{}" alt="{}"/><br/><hr/>\n'
                         .format(vu, svg, svg))
            else:
                html += ('<h2>{}</h2><p>ERROR: {}</p><hr/>\n'
                         .format(vu, svg))

    html += "</html>"
    with open('index.html', 'w') as f:
        f.write(html)

    print("View the files in {}".format(working_dir))

    print("Opening browser...")
    webbrowser.open(os.path.join(os.path.join(working_dir, 'index.html')))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Check consistency for all completed local stemmata by creating textual flow diagrams.")
    parser.add_argument('inputfile', help='file containing variant reading definitions')
    parser.add_argument('-c', '--connectivity', default=499, metavar='N', type=int,
                        help='Maximum allowed connectivity in a textual flow diagram')

    args = parser.parse_args()

    main(args.inputfile, args.connectivity)
