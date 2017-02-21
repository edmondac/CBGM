#!/usr/bin/env python
# encoding: utf-8

import os
import sys
import tempfile
import webbrowser
import logging

from copy import deepcopy
from itertools import product
from .populate_db import populate, Reading, LacunaReading, parse_input_file
from .lib.shared import UNCL, INIT, LAC, OL_PARENT
from .lib.textual_flow import textual_flow
from .lib.genealogical_coherence import CyclicDependency
from .lib import mpisupport

logger = logging.getLogger(__name__)


def single_hypothesis(stemmata, unique_ref, all_mss, force,
                      vu, connectivity, perfect_only, working_dir, *unused):
    """
    Generate the textual flow diagram for this variant unit in this set of stemmata
    """
    # Do this in our own temp dir
    mytemp = tempfile.mkdtemp()
    os.chdir(mytemp)
    # 1. Populate the db
    db = '{}_{}.db'.format(vu.replace('/', '.'), unique_ref)
    populate(stemmata, all_mss, db, force)

    # 2. Make the textual flow diagram
    try:
        of = textual_flow(db, [vu], [connectivity], perfect_only, force_serial=True)
        svg = of[connectivity] + '.svg'
    except CyclicDependency:
        return None

    # Copy it into the main working dir
    new_svg = '{}_{}'.format(unique_ref, os.path.basename(svg))
    os.makedirs(working_dir, exist_ok=True)
    os.rename(svg, os.path.join(working_dir, new_svg))
    return new_svg


class Hypotheses(mpisupport.MpiParent):
    def __init__(self, data, all_mss, vu, force=False,
                 perfect_only=True, connectivity=499, mpi=False):
        if mpi:
            super().__init__()
        self.data = data
        self.all_mss = all_mss
        self.vu = vu
        self.force = force
        self.perfect_only = perfect_only
        self.connectivity = connectivity
        self.results = {}
        self.working_dir = tempfile.mkdtemp()
        os.chdir(self.working_dir)
        self.mpi = mpi
        self.hypotheses()

    def hypotheses(self):
        """
        Take a variant unit and create an html page with textual flow diagrams for all
        potential hypotheses for UNCL readings.
        """
        v, u = self.vu.split('/')
        readings = self.data[v][u]
        unclear = [x for x in readings if x.parent == UNCL]
        parent_is_known = bool([x for x in readings if x.parent in (INIT, OL_PARENT)])
        changes = iter_permutations(unclear,
                                    [x.label for x in readings if x.label != LAC],
                                    not parent_is_known)
        # 'changes' is a generator yielding tuples, each one corresponding to a
        # single set of changes to make to the data.
        unique = 0
        for ch in changes:
            new_readings = []
            i = 0
            desc = []
            for x in readings:
                if isinstance(x, LacunaReading):
                    new_readings.append(x)
                    continue

                if x.parent == UNCL:
                    par = ch[i]
                    # Special case for INIT/OL_PARENT
                    if par == '_':
                        par = INIT  # For this it doesn't matter if we call it INIT or OL_PARENT
                    r = Reading(x.label, x.greek, x._ms_support, par)
                    new_readings.append(r)
                    desc.append("{} -> {}".format(r.parent, r.label))
                    i += 1
                else:
                    new_readings.append(x)

            my_stemmata = deepcopy(self.data)
            my_stemmata[v][u] = new_readings
            if self.mpi:
                self.mpi_queue.put((my_stemmata, unique,
                                    self.all_mss, self.force,
                                    self.vu, self.connectivity,
                                    self.perfect_only,
                                    self.working_dir,
                                    ', '.join(desc)))
            else:
                try:
                    svg = single_hypothesis(my_stemmata, unique,
                                            self.all_mss, self.force,
                                            self.vu, self.connectivity,
                                            self.perfect_only,
                                            self.working_dir)
                except Exception as e:
                    raise
                    print("ERROR doing {}, {}".format(ch, e))
                    self.results[unique] = (', '.join(desc), e)
                else:
                    self.results[unique] = (', '.join(desc), svg)

            unique += 1

        if self.mpi:
            self.mpi_wait()

        html = ("<html><h1>Hypotheses for {} (connectivity={})</h1>"
                .format(self.vu, self.connectivity))
        if self.perfect_only:
            html += "<p>Only showing perfect coherence - forests are hidden</p>"
        for desc, svg in self.results.values():
            if svg is not None and 'svg' in svg:
                html += ('<h2>{}</h2><img width="500px" src="{}" alt="{}"/><br/><hr/>\n'
                         .format(desc, svg, svg))
            else:
                html += ('<h2>{}</h2><p>ERROR: {}</p><hr/>\n'
                         .format(desc, svg))
        html += "</html>"

        out_f = os.path.join(self.working_dir, 'index.html')
        with open(out_f, 'w') as fh:
            fh.write(html)

        print("View the files in {}/{}".format(self.working_dir, out_f))

        print("Opening browser...")
        webbrowser.open(os.path.join(self.working_dir, out_f))

    def mpi_handle_result(self, args, ret):
        """
        Handle an MPI result
        @param args: original args sent to the child
        @param ret: response from the child
        """
        desc = args[-1]
        unique_ref = args[1]
        if ret is None:
            # error calculating this one
            self.results[unique_ref] = (desc, 'ERROR DETECTED')
        else:
            # recreate the svg locally
            with open(ret['svgname'], 'wb') as f:
                f.write(ret['svgdata'])

            self.results[unique_ref] = (desc, ret['svgname'])


def mpi_single_hypothesis(*args):
    """
    Wrapper for an MPI single hypothesis call
    """
    svg = single_hypothesis(*args)
    if svg is None:
        return None
    else:
        working_dir = args[7]
        with open(os.path.join(working_dir, svg), 'rb') as f:
            return {'svgname': svg, 'svgdata': f.read()}


def iter_permutations(unclear, potential_parents, can_designate_generation_zero):
    """
    Find all possible permutations of unclear elements
    """
    assert LAC not in potential_parents

    # Only things marked as UNCL can change their parent
    # If there's no INIT/OL_PARENT, then any UNCL could be the INIT/OL_PARENT
    if can_designate_generation_zero:
        for i, unc in enumerate(unclear):
            ch = [None for x in unclear]
            ch[i] = '_'
            for j, inner in enumerate(unclear):
                if i == j:
                    continue
                ch[j] = [x for x in potential_parents if x != inner.label]
            yield from product(*ch)
    else:
        for i, unc in enumerate(unclear):
            ch = [None for x in unclear]
            ch[i] = [x for x in potential_parents if x != unc.label]
            yield from product(*ch)


def find_ancestors(ch_map, node):
    """
    Return a list of all ancestors of the supplied node in the change map
    """
    ret = [ch_map[node]] if node in ch_map else []
    if node in ch_map:
        ret.extend(find_ancestors(ch_map, ch_map[node]))
    return ret


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Make textual flow diagrams for hypotheses")
    parser.add_argument('inputfile', help='file containing variant reading definitions')
    parser.add_argument('-v', '--variant-unit', default=None, required=True,
                        help="Show extra data about this variant unit (e.g. 1/2-8)")
    parser.add_argument('--force', default=False, action='store_true',
                        help='force mode - overwrite any files that get in the way')
    parser.add_argument('-p', '--perfect', default=False, action='store_true',
                        help='perfect coherence - reject forests')
    parser.add_argument('-c', '--connectivity', default=499, metavar='N', type=int,
                        help='Maximum allowed connectivity in a textual flow diagram')
    parser.add_argument('-s', '--single', default=False, action='store_true',
                        help='Use the single process version (MPI-enabled is default)')

    parser.add_argument('--verbose', action='count')

    args = parser.parse_args()

    h1 = logging.StreamHandler(sys.stderr)
    rootLogger = logging.getLogger()
    rootLogger.addHandler(h1)
    formatter = logging.Formatter('[%(asctime)s] [%(process)s] [%(filename)s:%(lineno)s] [%(levelname)s] %(message)s')
    h1.setFormatter(formatter)

    if args.verbose:
        rootLogger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode")
    else:
        rootLogger.setLevel(logging.INFO)
        logger.debug("Run with --verbose for debug mode")

    is_parent = True
    if not args.single:
        if 'OMPI_COMM_WORLD_SIZE' not in os.environ:
            # Not run with mpiexec
            print("Running in MPI mode but not executed by mpiexec - aborting")
            print("Consider running with '-s' or using, e.g., 'mpiexec -np 4'")
            print("Also consider making a hostfile for mpiexec.")
            sys.exit(2)

        is_parent = mpisupport.is_parent()

    if is_parent:
        # parent or only process
        struct, all_mss = parse_input_file(args.inputfile)
        Hypotheses(struct, all_mss, args.variant_unit, args.force, args.perfect,
                   args.connectivity, not args.single)
    else:
        # child
        mpisupport.mpi_child(mpi_single_hypothesis)
