# encoding: utf-8

import subprocess
import sqlite3
import networkx
from .genealogical_coherence import GenealogicalCoherence


class ForestError(Exception):
    pass


def textual_flow(db_file, variant_unit, connectivity,
                 perfect_only=False):
    """
    Create a textual flow diagram for the specified variant unit.
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
        best_parent = None
        for row in coh.rows:
            if row['_RANK'] > connectivity:
                # Exceeds connectivity setting
                continue
            if row['D'] == '-':
                # Not a potential ancestor (undirected genealogical coherence)
                continue
            if row['READING'] == w1_reading:
                # This matches our reading and is within the connectivity threshold - take it
                best_parent = row
                break
            if row['READING'] == w1_parent and best_parent is None:
                # Take the best row where the reading matches our parent reading
                best_parent = row

        if best_parent is None or best_parent['_RANK'] == 1:
            rank_mapping[w1] = "{} ({})".format(w1, w1_reading)
        else:
            rank_mapping[w1] = "{}/{} ({})".format(w1, best_parent['_RANK'], w1_reading)

        if not best_parent:
            if w1 == 'A':
                # That's ok...
                continue
            elif perfect_only:
                raise ForestError("Nodes with no parents - forest detected")

            print("WARNING - {} has no parents".format(w1))
            continue

        G.add_edge(best_parent['W2'], w1)

    # Relable nodes to include the rank
    networkx.relabel_nodes(G, rank_mapping, copy=False)

    print("Creating graph with {} nodes and {} edges".format(G.number_of_nodes(),
                                                             G.number_of_edges()))
    networkx.write_dot(G, 'test.dot')

    output_file = "textual_flow_{}_c{}.svg".format(variant_unit.replace('/', '_'), connectivity)
    subprocess.check_call(['dot', '-Tsvg', 'test.dot'], stdout=open(output_file, 'w'))

    print("Written to {}".format(output_file))

    return output_file
