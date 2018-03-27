#!/bin/bash
# This runs the unit tests and coverage checking

set -x

cd $(dirname $0)

coverage run --source=. -m unittest discover
