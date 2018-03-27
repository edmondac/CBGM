#!/bin/bash
# This runs the unit tests and coverage checking

set -x

cd $(dirname $0)

# Note that our PYTHONPATH already allows imports like "from CBGM import populate_db"

coverage run --source=. -m unittest discover
