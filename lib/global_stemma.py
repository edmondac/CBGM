#!/usr/bin/env python
# encoding: utf-8
# Script to create the global stemma

import importlib
import sys
import networkx
from tempfile import NamedTemporaryFile
import subprocess
import populate_db
from lib.genealogical_coherence import GenealogicalCoherence

DEFAULT_DB_FILE = '/tmp/glob_stem.db'


def load(inputfile):
    """
    Load the specified file and return the optimal_substemmata object
    """
    # We need to add . to the path, so we can import the specified python file
    # even if this script has been called by a full path.
    sys.path.append(".")

    if inputfile.endswith('.py'):
        inputfile = inputfile[:-3]
    mod = importlib.import_module(inputfile)
    return mod.optimal_substemmata


def pick_best(w1, combinations, dbfile):
    """
    Pick the best of the supplied combinations, looking for the combination of
    highest ranking potential ancestors.
    """
    gc = GenealogicalCoherence(dbfile, w1)
    gc._generate()

    def rank(w2):
        for row in gc.rows:
            if row['W2'] == w2.replace('P', '𝔓'):
                return row['_RANK']
        else:
            # import pdb; pdb.set_trace()
            raise ValueError("Couldn't find {} in pot anc of {}".format(w2, gc.w1))

    best_rank = None
    best_comb = None
    for combination in combinations:
        ranks = [rank(x) for x in combination]
        avg_rank = sum(ranks) / float(len(ranks))
        if best_rank is None or avg_rank < best_rank:
            best_rank = avg_rank
            best_comb = combination
        elif best_rank == avg_rank:
            raise ValueError("Two combinations have the same average rank")

    assert best_comb is not None
    return best_comb


def optimal_substemma(inputfile, w1):
    """
    Create an image for the optimal substemma of a particular witness.
    """
    output_file = 'optimal_substemma_{}.svg'.format(w1)

    populate_db.main(inputfile, DEFAULT_DB_FILE, force=True)
    optsub = load(inputfile)
    comb_anc = optsub[w1]

    print("{}: {}".format(w1, comb_anc))
    best = pick_best(w1, comb_anc, DEFAULT_DB_FILE)

    print(" > {}".format(best))
    nodes = {x for x in best}
    edges = {(x, w1) for x in nodes}
    for node in best:
        if '<' in node:
            # This is an intermediary node...
            for newnode in node.split('<'):
                nodes.add(newnode)
                edges.add((node, newnode))

                if newnode != w1:
                    # Need the parents of this one too...
                    other_best = pick_best(newnode, optsub[newnode], DEFAULT_DB_FILE)
                    for other_p in other_best:
                        if other_p in nodes:
                            # Only include parents that we've already got, since
                            # we're creating the optimal substemma of w1 not
                            # newnode.
                            edges.add((other_p, newnode))

            for parent in best:
                if parent != node:
                    edges.add((parent, node))

        assert '>' not in node, "Intermediary nodes should be specified with '<'"

    print(nodes)
    print(edges)

    G = networkx.DiGraph()
    G.add_nodes_from(nodes)
    for pri, post in edges:
        G.add_edge(pri, post)

    print("Creating graph with {} nodes and {} edges".format(G.number_of_nodes(),
                                                             G.number_of_edges()))
    with NamedTemporaryFile() as dotfile:
        networkx.write_dot(G, dotfile.name)
        subprocess.check_call(['dot', '-Tsvg', dotfile.name, '-o', output_file])

    print("Written diagram to {}".format(output_file))


def global_stemma(inputfile):
    """
    Make the global stemma
    """
    output_file = 'global_stemma.svg'

    populate_db.main(inputfile, DEFAULT_DB_FILE, force=True)
    glob_stem = {}
    optsub = load(inputfile)
    for w1, comb_anc in optsub.items():
        print("{}: {}".format(w1, comb_anc))
        best = pick_best(w1, comb_anc, DEFAULT_DB_FILE)
        print(" > {}".format(best))
        glob_stem[w1] = best

    G = networkx.DiGraph()
    G.add_nodes_from(optsub.keys())
    for w1, comb in glob_stem.items():
        for w2 in comb:
            G.add_edge(w2, w1)

    print("Creating graph with {} nodes and {} edges".format(G.number_of_nodes(),
                                                             G.number_of_edges()))
    with NamedTemporaryFile() as dotfile:
        networkx.write_dot(G, dotfile.name)
        subprocess.check_call(['dot', '-Tsvg', dotfile.name, '-o', output_file])

    print("Written diagram to {}".format(output_file))
