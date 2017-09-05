# -*- coding: utf-8 -*-
#!/usr/bin/python

import sys
import importlib
import unicodedata
from .shared import LAC, INIT

MISSING = "-"
GAP = "?"


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
    return mod.struct, sorted(mod.all_mss)


def sanitise_wit(wit):
    """
    MrBayes doesn't like some chars in taxon names
    """
    conv = []
    for char in unicodedata.normalize('NFD', wit):
        name = unicodedata.name(char)
        if name.split()[0] not in ('DIGIT', 'LATIN'):
            rep = 'U{}'.format(ord(char))
            print("Converting character '{}' ({}) in '{}' to '{}'".format(char, name, wit, rep))
            conv.append((char, rep))

    for f, t in conv:
        wit = wit.replace(f, t)

    return wit

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
    witnesses_copy = witnesses[:] + ['A']
    for i, wit in enumerate(witnesses_copy):
        sys.stdout.write("\r{}/{}: {}    ".format(i + 1, len(witnesses_copy), wit))
        sys.stdout.flush()
        stripe = []
        for verse in sorted(struct):
            for vu in sorted(struct[verse]):
                sig = None
                for reading in struct[verse][vu]:
                    if wit == 'A':
                        if reading.parent == INIT:
                            sig = reading.label
                    else:
                        reading.calc_mss_support(witnesses)
                        if reading.ms_support and wit in reading.ms_support:
                            if reading.label == LAC:
                                sig = MISSING
                            else:
                                sig = reading.label

                if not sig:
                    if wit == 'A':
                        sig = MISSING
                    else:
                        raise ValueError("Witness {} not found in VU {}/{}".format(wit, verse, vu))
                if len(sig) > 1:
                    # Corner case, like multiple parents. Treat as missing...
                    sig = MISSING
                stripe.append(sig)

        this_count = len([x for x in stripe if x != MISSING])
        if this_count > target:
            matrix.append("{} {}".format(sanitise_wit(wit), ''.join(stripe)))
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
           "\n".join(sanitise_wit(x) for x in witnesses),
           len(all_vus),
           MISSING,
           GAP,
           ' '.join(sorted(list(symbols))),
           '\n'.join(matrix))

    with open(output_file, 'w') as fh:
        fh.write(nexus_data)

    print("\nWrote {}".format(output_file))
