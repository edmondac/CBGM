# encoding: utf-8

import subprocess
import sqlite3
import networkx
import string
import os
from tempfile import NamedTemporaryFile
from .shared import OL_PARENT
from .genealogical_coherence import GenealogicalCoherence
from lib import mpisupport

# Colours from http://www.hitmill.com/html/pastels.html
COLOURS = ("#FF8A8A", "#FF86E3", "#FF86C2", "#FE8BF0", "#EA8DFE", "#DD88FD", "#AD8BFE",
           "#FFA4FF", "#EAA6EA", "#D698FE", "#CEA8F4", "#BCB4F3", "#A9C5EB", "#8CD1E6",
           "#8C8CFF", "#99C7FF", "#99E0FF", "#63E9FC", "#74FEF8", "#62FDCE", "#72FE95",
           "#4AE371", "#80B584", "#89FC63", "#36F200", "#66FF00", "#DFDF00", "#DFE32D")

# with open('/tmp/col.html', 'w') as f:
#     colours = ""
#     for col in COLOURS:
#         colours += '<table><tr><td bgcolor="{}">HELLO THERE {}</td></tr></table>\n'.format(col, col)
#     f.write("""<html>{}</html>""".format(colours))

COLOURMAP = {x: COLOURS[(i * 10) % len(COLOURS)]
             for (i, x) in enumerate(string.ascii_lowercase)}


def darken(col, by=75):
    """
    Darken a colour by specified amount
    """
    assert col[0] == '#'
    r, g, b = int(col[1:3], 16), int(col[3:5], 16), int(col[5:7], 16)

    def dark(x, by=by):
            new = max(x - by, 0)
            return str(hex(new))[2:]

    return '#{}{}{}'.format(dark(r), dark(g), dark(b))


class ForestError(Exception):
    pass


def get_parents(w1, w1_reading, w1_parent, variant_unit, connectivity, db_file):
    """
    Calculate the best parents for this witness at this variant unit

    This can take a long time...
    """
    print("Calculating genealogical coherence for {} at {}".format(w1, variant_unit))
    coh = GenealogicalCoherence(db_file, w1, variant_unit, pretty_p=False)
    coh._generate()
    # we might need multiple parents if a reading requires it
    best_parents_by_rank = []
    best_rank = None
    best_parents_by_gen = []
    best_gen = None
    parents = []
    max_acceptable_gen = 2  # only allow my reading or my parent's
    for combination in coh.parent_combinations(w1_reading, w1_parent, connectivity):
        if not combination:
            # Couldn't find anything to explain it
            print("Couldn't find any parent combination for {}".format(w1_reading))
            continue

        rank = max(x[1] for x in combination)
        gen = max(x[2] for x in combination)
        if gen > max_acceptable_gen:
            continue

        if best_gen is None or gen < best_gen:
            best_parents_by_gen = combination
            best_gen = gen
        elif gen == best_gen:
            if rank < max(x[1] for x in best_parents_by_gen):
                # This is a better option for this generation
                best_parents_by_gen = combination
                best_gen = gen

        if best_rank is None or rank < best_rank:
            best_parents_by_rank = combination
            best_rank = rank

    if best_gen == 1:
        # We can do this with direct parents - use them
        parents = best_parents_by_gen
    else:
        # Got to use ancestors, so use the best by rank
        parents = best_parents_by_rank

    if w1_parent == OL_PARENT and not parents:
        # Top level in an overlapping unit with an omission in the initial text
        parents = [('OL_PARENT', -1, 1)]

    print(" > Best parents: {}".format(parents))

    return parents


def textual_flow(db_file, variant_unit, connectivity, perfect_only=False, suffix=''):
    """
    Create a textual flow diagram for the specified variant unit. This will
    work out if we're using MPI and act accordingly...
    """
    if 'OMPI_COMM_WORLD_SIZE' in os.environ:
        # We have been run with mpiexec
        mpi_parent = mpisupport.is_parent()
        mpi_mode = True
    else:
        mpi_mode = False

    if mpi_mode:
        if mpi_parent:
            return TextualFlow(db_file, variant_unit, connectivity, perfect_only=False, suffix='', mpi=True)
        else:
            # MPI child
            mpisupport.mpi_child(get_parents)

    else:
        return TextualFlow(db_file, variant_unit, connectivity, perfect_only=False, suffix='')


class TextualFlow(mpisupport.MpiParent):
    def __init__(self, db_file, variant_unit, connectivity, perfect_only=False, suffix='', mpi=False):
        self.mpi = mpi
        super().__init__()
        self.db_file = db_file
        self.variant_unit = variant_unit
        self.connectivity = connectivity
        self.perfect_only = perfect_only
        self.suffix = suffix
        self.parent_map = {}
        self.textual_flow()

    def mpi_run(self):
        """
        Simple wrapper to handle mpi on or off.
        """
        if self.mpi:
            return super().mpi_run()
        else:
            pass

    def textual_flow(self):
        """
        Create a textual flow diagram for the specified variant unit.

        Because I put the whole textual flow in one diagram (unlike Munster who
        show a textual flow diagram for a single reading) there can be multiple
        ancestors for a witness...
        """

        print("Creating textual flow diagram for {}".format(self.variant_unit))
        print("Setting connectivity to {}".format(self.connectivity))
        if self.perfect_only:
            print("Insisting on perfect coherence...")
        G = networkx.DiGraph()

        sql = """SELECT witness, label, parent
                 FROM attestation, reading
                 WHERE attestation.reading_id = reading.id
                 AND reading.variant_unit = \"{}\"
                 """.format(self.variant_unit)
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        data = list(cursor.execute(sql))
        # get the colour for the first char of the label (e.g. for b1 just get b)
        witnesses = [(x[0], {'color': darken(COLOURMAP.get(x[1][0], '#cccccc')),
                             'fillcolor': COLOURMAP.get(x[1][0], '#cccccc'),
                             'style': 'filled'})  # See http://www.graphviz.org/
                     for x in data]
        G.add_nodes_from(witnesses)

        # 1. Calculate the best parent for each witness
        for i, (w1, w1_reading, w1_parent) in enumerate(data):
            print("Calculating parents {}/{}".format(i, len(data)))
            if self.mpi:
                self.mpi_queue.put((w1, w1_reading, w1_parent, self.variant_unit, self.connectivity, self.db_file))
            else:
                parents = get_parents(w1, w1_reading, w1_parent, self.variant_unit, self.connectivity, self.db_file)
                self.parent_map[w1] = parents

        if self.mpi:
            self.mpi_wait()
            # Now self.parent_map should be complete

        print("Parent map is: {}".format(self.parent_map))

        # 2. Draw the diagram
        rank_mapping = {}
        for w1, w1_reading, w1_parent in data:
            parents = self.parent_map[w1]
            if len(parents) > 1:
                # Multiple parents - caused by a reading with multiple parents in
                # a local stemma.
                rank_mapping[w1] = "{}/[{}] ({})".format(
                    w1, ', '.join("{}.{}".format(x[0], x[1]) for x in parents), w1_reading)
            elif len(parents) == 1:
                # Just one parent
                if parents[0][1] == 1:
                    rank_mapping[w1] = "{} ({})".format(w1, w1_reading)
                else:
                    rank_mapping[w1] = "{}/{} ({})".format(w1, parents[0][1], w1_reading)
            else:
                # no parents
                rank_mapping[w1] = "{} ({})".format(w1, w1_reading)

            if all(x[0] is None for x in parents):
                if w1 == 'A':
                    # That's ok...
                    continue

                elif self.perfect_only:
                    raise ForestError("Nodes with no parents - forest detected")

                print("WARNING - {} has no parents".format(w1))
                continue

            for i, p in enumerate(parents):
                G.add_edge(p[0], w1)

        # Relable nodes to include the rank
        networkx.relabel_nodes(G, rank_mapping, copy=False)

        print("Creating graph with {} nodes and {} edges".format(G.number_of_nodes(),
                                                                 G.number_of_edges()))
        output_file = "textual_flow_{}_c{}{}.svg".format(
            self.variant_unit.replace('/', '_'), self.connectivity, self.suffix)
        with NamedTemporaryFile() as dotfile:
            networkx.write_dot(G, dotfile.name)
            subprocess.check_call(['dot', '-Tsvg', dotfile.name], stdout=open(output_file, 'w'))

        print("Written to {}".format(output_file))

        return output_file

    def mpi_handle_result(self, args, ret):
        """
        Handle an MPI result
        @param args: original args sent to the child
        @param ret: response from the child
        """
        w1 = args[0]
        self.parent_map[w1] = ret
