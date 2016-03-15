# encoding: utf-8

import subprocess
import sqlite3
import networkx
import string
from tempfile import NamedTemporaryFile
from .shared import OL_PARENT
from .genealogical_coherence import GenealogicalCoherence

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


def textual_flow(db_file, variant_unit, connectivity,
                 perfect_only=False, prefix=''):
    """
    Create a textual flow diagram for the specified variant unit.

    Because I put the whole textual flow in one diagram (unlike Munster who
    show a textual flow diagram for a single reading) there can be multiple
    ancestors for a witness...
    """
    print("Creating textual flow diagram for {}".format(variant_unit))
    print("Setting connectivity to {}".format(connectivity))
    if perfect_only:
        print("Insisting on perfect coherence...")
    G = networkx.DiGraph()

    sql = """SELECT witness, label, parent
             FROM attestation, reading
             WHERE attestation.reading_id = reading.id
             AND reading.variant_unit = \"{}\"
             """.format(variant_unit)
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    data = list(cursor.execute(sql))
    # get the colour for the first char of the label (e.g. for b1 just get b)
    witnesses = [(x[0], {'color': darken(COLOURMAP.get(x[1][0], '#cccccc')),
                         'fillcolor': COLOURMAP.get(x[1][0], '#cccccc'),
                         'style': 'filled'})  # See http://www.graphviz.org/
                 for x in data]
    G.add_nodes_from(witnesses)

    rank_mapping = {}
    for w1, w1_reading, w1_parent in data:
        print("Calculating genealogical coherence for {} at {}".format(w1, variant_unit))
        coh = GenealogicalCoherence(db_file, w1, variant_unit, False)
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

            elif perfect_only:
                raise ForestError("Nodes with no parents - forest detected")

            print("WARNING - {} has no parents".format(w1))
            continue

        for i, p in enumerate(parents):
            G.add_edge(p[0], w1)

    # Relable nodes to include the rank
    networkx.relabel_nodes(G, rank_mapping, copy=False)

    print("Creating graph with {} nodes and {} edges".format(G.number_of_nodes(),
                                                             G.number_of_edges()))
    output_file = "{}textual_flow_{}_c{}.svg".format(
        prefix, variant_unit.replace('/', '_'), connectivity)
    with NamedTemporaryFile() as dotfile:
        networkx.write_dot(G, dotfile.name)
        subprocess.check_call(['dot', '-Tsvg', dotfile.name], stdout=open(output_file, 'w'))

    print("Written to {}".format(output_file))

    return output_file
