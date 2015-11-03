#!/usr/bin/env python
# encoding: utf-8

import os
import sys
import tempfile
import webbrowser
import threading
import queue
from copy import deepcopy
from itertools import product
from populate_db import populate, Reading, LacunaReading, parse_input_file
from lib.shared import UNCL, INIT, LAC
from lib.textual_flow import textual_flow
from lib.genealogical_coherence import CyclicDependency


class Hypotheses(object):
    def __init__(self, data, all_mss, vu, force=False,
                 perfect_only=True, connectivity=499,
                 mpi=False):
        self.data = data
        self.all_mss = all_mss
        self.vu = vu
        self.force = force
        self.perfect_only = perfect_only
        self.connectivity = connectivity
        self.results = {}
        self.working_dir = tempfile.mkdtemp()
        os.chdir(self.working_dir)

        self.mpicomm = None
        self.mpi_queue = queue.Queue()
        self.mpi_child_threads = []
        self.mpi = mpi
        if mpi:
            self.mpi_run()
        else:
            self.hypotheses()

    def single_hypothesis(self, stemmata, unique_ref):
        """
        Generate the textual flow diagram for this variant unit in this set of stemmata
        """
        # 1. Populate the db
        db = '{}_{}.db'.format(self.vu.replace('/', '.'), unique_ref)
        populate(stemmata, self.all_mss, db, self.force)

        # 2. Make the textual flow diagram
        try:
            svg = textual_flow(db, self.vu, self.connectivity, self.perfect_only)
        except CyclicDependency:
            return None

        new_svg = '{}_{}'.format(unique_ref, svg)
        os.rename(svg, new_svg)
        return new_svg

    def hypotheses(self):
        """
        Take a variant unit and create an html page with textual flow diagrams for all
        potential hypotheses for UNCL readings.
        """
        v, u = self.vu.split('/')
        readings = self.data[v][u]
        unclear = [x for x in readings if x.parent == UNCL]
        initial_text = [x for x in readings if x.parent == INIT]
        changes = find_permutations(unclear,
                                    [x.label for x in readings if x.label != LAC],
                                    not initial_text)
        # 'changes' is a list of tuples, each one corresponding to a single
        # set of changes to make to the data.
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
                    # Special case for INIT
                    if par == '_':
                        par = INIT
                    r = Reading(x.label, x.greek, x._ms_support, par)
                    new_readings.append(r)
                    desc.append("{} -> {}".format(r.parent, r.label))
                    i += 1
                else:
                    new_readings.append(x)

            my_stemmata = deepcopy(self.data)
            my_stemmata[v][u] = new_readings
            if self.mpi:
                self.mpi_queue.put((my_stemmata, unique, ', '.join(desc)))
            else:
                try:
                    svg = self.single_hypothesis(my_stemmata, unique)
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
            if 'svg' in svg:
                html += ('<h2>{}</h2><img width="500px" src="{}" alt="{}"/><br/><hr/>\n'
                         .format(desc, svg, svg))
            else:
                html += ('<h2>{}</h2><p>ERROR: {}</p><hr/>\n'
                         .format(desc, svg))
        html += "</html>"

        out_f = 'index.html'
        with open(out_f, 'w') as fh:
            fh.write(html)

        print("View the files in {}/{}".format(self.working_dir, out_f))

        print("Opening browser...")
        webbrowser.open(os.path.join(self.working_dir, out_f))

    def mpi_wait(self):
        """
        Wait for all work to be done, then tell things to stop
        """
        # When the queue is done, we can continue. The child threads
        # have daemon=True and will just exit.
        self.mpi_queue.join()

        for child in range(1, self.mpicomm.size):
            # Tell the remote child processes to exit
            self.mpicomm.send(None, dest=child)

    def mpi_manage_child(self, child):
        """
        Manage communications with the specified MPI child
        """
        print("Child manager {} starting".format(child))
        while True:
            # wait for something to do
            stemmata, unique_ref, desc = self.mpi_queue.get()

            # send it to the remote child
            self.mpicomm.send({'stemmata': stemmata,
                               'unique_ref': unique_ref}, dest=child)

            # get the results back
            ret = self.mpicomm.recv(source=child)
            if ret is None:
                # error calculating this one
                self.results[unique_ref] = (desc, 'ERROR DETECTED')
            else:
                # recreate the svg locally
                with open(ret['svgname'], 'wb') as f:
                    f.write(ret['svgdata'])

                self.results[unique_ref] = (desc, ret['svgname'])

            self.mpi_queue.task_done()

    def mpi_run(self):
        """
        Top-level MPI method. Works out if we're a parent or child and
        acts accordingly.
        """
        from mpi4py import MPI
        self.mpicomm = MPI.COMM_WORLD
        rank = self.mpicomm.Get_rank()
        if rank == 0:
            # parent
            print("MPI-enabled version with {} processors available"
                  .format(self.mpicomm.size))
            for child in range(1, self.mpicomm.size):
                t = threading.Thread(target=self.mpi_manage_child,
                                     args=(child, ),
                                     daemon=True)
                t.start()
                self.mpi_child_threads.append(t)

            self.hypotheses()
        else:
            print("Child {} starting".format(rank))
            while True:
                # child - wait to be given a data structure
                data = self.mpicomm.recv(source=0)
                if data is None:
                    print("Child {} exiting".format(rank))
                    break
                print("Child {} received data".format(rank))
                svg = self.single_hypothesis(data['stemmata'],
                                             data['unique_ref'])
                if svg is None:
                    # Nothing was generated
                    self.mpicomm.send(None)
                    print("Child {} aborted job".format(rank))
                else:
                    with open(svg, 'rb') as f:
                        self.mpicomm.send({'svgname': svg,
                                           'svgdata': f.read()})
                    print("Child {} completed job".format(rank))


def find_permutations(unclear, potential_parents, can_designate_initial_text):
    """
    Find all possible permutations of unclear elements
    """
    assert LAC not in potential_parents

    # Only things marked as UNCL can change their parent
    # If there's no INIT, then any UNCL could be the INIT
    changes = []
    if can_designate_initial_text:
        for i, unc in enumerate(unclear):
            ch = [None for x in unclear]
            ch[i] = '_'
            for j, inner in enumerate(unclear):
                if i == j:
                    continue
                ch[j] = [x for x in potential_parents if x != inner.label]
            changes.extend(product(*ch))
    else:
        for i, unc in enumerate(unclear):
            ch = [None for x in unclear]
            ch[i] = [x for x in potential_parents if x != unc.label]
            changes.extend(product(*ch))

    # Look for cycle
    good_changes = []
    for ch in changes:
        change_map = {}
        for i, unc in enumerate(unclear):
            goto = ch[i]
            ancestors = find_ancestors(change_map, goto)
            if unc.label in ancestors:
                # This would be a loop
                break
            change_map[unc.label] = ch[i]
        else:
            # No break - must be good
            good_changes.append(ch)

    return good_changes


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

    args = parser.parse_args()
    if not args.single:
        if not 'OMPI_COMM_WORLD_SIZE' in os.environ:
            # Not run with mpiexec
            print("Running in MPI mode but not executed by mpiexec - aborting")
            print("Consider running with '-s' or using, e.g., 'mpiexec -np 4'")
            sys.exit(2)

    struct, all_mss = parse_input_file(args.inputfile)
    Hypotheses(struct, all_mss, args.variant_unit, args.force, args.perfect,
               args.connectivity, not args.single)
