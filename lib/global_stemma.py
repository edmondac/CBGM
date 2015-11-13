#!/usr/bin/env python
# encoding: utf-8
# Script to create the global stemma

import os
import importlib
import sys


def load(filename):
    """
    Load the specified file and return the optimal_substemmata object
    """
    # We need to add . to the path, so we can import the specified python file
    # even if this script has been called by a full path.
    sys.path.append(".")

    if filename.endswith('.py'):
        filename = filename[:-3]
    mod = importlib.import_module(filename)
    return mod.optimal_substemmata


def global_stemma(filename):
    """
    Make the global stemma
    """
    optsub = load(filename)
    for witness, comb_anc in optsub:
        print("{}: {}".format(witness, comb_anc))
