#!/bin/bash
# This runs the unit tests and coverage checking

cd $(dirname $0)

# Note that our PYTHONPATH already allows imports like "from CBGM import populate_db"

coverage run --source=. -m unittest discover $@

coverage report

if [[ "X$1" != "X-v" ]]; then
    echo "Hint: Run this script with -v to get debugging output"
fi
