# -*- coding: utf-8 -*-
#!/usr/bin/python

import sys
import string
import importlib
from .shared import LAC

MISSING = "-"
# We won't actually use GAP here, since Phylogenetic software (e.g. MrBayes)
# tends to treat missing and gap the same anyway...
GAP = "?"

_possible_symbols = list(string.ascii_letters) + list(string.digits)
_sym_map = {}


def get_symbol(x):
    """
    Return an appropriate symbol to use for MyBayes, always returning the
    same symbol for the same input.
    """
    if x in _sym_map:
        return _sym_map[x]
    else:
        sym = _possible_symbols.pop(0)
        _sym_map[x] = sym
        return sym


def load(inputfile):
    """
    Load the specified file and return the data
    """
    # We need to add . to the path, so we can import the specified python file
    # even if this script has been called by a full path.
    sys.path.append(".")

    if inputfile.endswith('.py'):
        inputfile = inputfile[:-3]
    mod = importlib.import_module(inputfile)
    return mod.struct, list(mod.all_mss)


def nexus(input_file, min_extant_perc, output_file):
    """
    Create a NEXUS file from the CBGM data

    @param struct: CBGM struct data
    @param witnesses: CBGM list of all manuscripts (hands) in data
    @param min_extant_perc: Minimum allowable extant data
    @param filename: Output filename
    """
    struct, witnesses = load(input_file)
    all_vus = []
    for verse in struct:
        for vu in struct[verse]:
            all_vus.append("{}/{}".format(verse, vu))

    target = len(witnesses) * min_extant_perc / 100.0
    print("Including only witnesses extant in {} ({}%) variant units".format(target, min_extant_perc))

    symbols = set()
    matrix = []
    witnesses_copy = witnesses[:]
    for i, wit in enumerate(witnesses_copy):
        sys.stdout.write("\r{}/{}: {}    ".format(i + 1, len(witnesses_copy), wit))
        sys.stdout.flush()
        stripe = []
        for verse in struct:
            for vu in struct[verse]:
                sig = None
                for reading in struct[verse][vu]:
                    reading.calc_mss_support(witnesses)
                    if reading.ms_support and wit in reading.ms_support:
                        if reading.label == LAC:
                            sig = MISSING
                        else:
                            sig = reading.label

                assert sig, "Witness {} not found in VU {}/{}".format(wit, verse, vu)
                stripe.append(sig)

        this_count = len([x for x in stripe if x != MISSING])
        if this_count > target:
            matrix.append("{} {}".format(wit, ''.join(stripe)))
        else:
            print("Deleting witness {} - it is only extant in {} variant unit(s)".format(wit, this_count))
            del witnesses[witnesses.index(wit)]

    nexus_data = """#nexus
BEGIN Taxa;
DIMENSIONS ntax={};
TAXLABELS
{}
;
END;
BEGIN Characters;
DIMENSIONS nchar={};

FORMAT
    datatype=STANDARD
    missing={}
    gap={}
    symbols="{}"
;
MATRIX
{}
;
END;
""".format(len(witnesses),
           "\n".join(witnesses),
           len(all_vus),
           MISSING,
           GAP,
           ' '.join(sorted(list(symbols))),
           '\n'.join(matrix))

    with open(output_file, 'w') as fh:
        fh.write(nexus_data)

    print("\nWrote {}".format(output_file))