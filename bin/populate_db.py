#!/usr/bin/env python
# Script to populate a sqlite database given a suitable input file

from CBGM.lib.populate_db import populate

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Populate sqlite database")
    parser.add_argument('inputfile', help='file containing variant reading definitions')
    parser.add_argument('dbfile', help='filename for new sqlite db')
    parser.add_argument('--force', default=False, action='store_true',
                        help='force mode - overwrite any files that get in the way')

    args = parser.parse_args()
    populate(args.inputfile, args.dbfile, force=args.force)
