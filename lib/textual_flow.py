# encoding: utf-8

import subprocess
import sqlite3
import networkx
from tempfile import NamedTemporaryFile

from .genealogical_coherence import GenealogicalCoherence


class ForestError(Exception):
    pass


def textual_flow(db_file, variant_unit, connectivity,
                 perfect_only=False):
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
    witnesses = [x[0] for x in data]
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
        for combination in coh.parent_combinations(w1_reading, w1_parent, connectivity):
            if not combination:
                # Couldn't find anything to explain it
                print("Couldn't find any parent combination for {}".format(w1_reading))
                continue

            rank = max(x[1] for x in combination)
            gen = max(x[2] for x in combination)
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
    output_file = "textual_flow_{}_c{}.svg".format(variant_unit.replace('/', '_'), connectivity)
    with NamedTemporaryFile() as dotfile:
        networkx.write_dot(G, dotfile.name)
        subprocess.check_call(['dot', '-Tsvg', dotfile.name], stdout=open(output_file, 'w'))

    print("Written to {}".format(output_file))

    return output_file
