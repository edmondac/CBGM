#!/usr/bin/env python
# encoding: utf-8
# Script to create the global stemma

import importlib
import sys
import networkx
from tempfile import NamedTemporaryFile
import subprocess
import populate_db

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


def nodes_and_edges(w1, comb_anc, optsub):
    """
    Calculate the nodes and edges for the supplied optimal substemma of w1
    """
    nodes = {x for x in comb_anc}
    edges = {(x, w1) for x in nodes}
    for node in comb_anc:
        if '<' in node:
            # This is an intermediary node...
            for newnode in node.split('<'):
                nodes.add(newnode)
                edges.add((node, newnode))

                if newnode != w1:
                    # Need the parents of this one too...
                    other_comb = optsub[newnode]
                    if len(other_comb) > 1:
                        raise ValueError("Can't draw a single optimal substemma")
                    for other_p in other_comb[0]:
                        if other_p in nodes:
                            # Only include parents that we've already got, since
                            # we're creating the optimal substemma of w1 not
                            # newnode.
                            edges.add((other_p, newnode))

            for parent in comb_anc:
                if parent != node:
                    edges.add((parent, node))

        assert '>' not in node, "Intermediary nodes should be specified with '<'"

    return nodes, edges


def optimal_substemma(inputfile, w1):
    """
    Create an image for the optimal substemma of a particular witness.
    """
    output_file = 'optimal_substemma_{}.svg'.format(w1)

    populate_db.main(inputfile, DEFAULT_DB_FILE, force=True)
    optsub = load(inputfile)
    comb_anc = optsub[w1]

    print("{}: {}".format(w1, comb_anc))

    if len(comb_anc) > 1:
        raise ValueError("Can't draw a single optimal substemma")

    nodes, edges = nodes_and_edges(w1, comb_anc[0], optsub)
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
    optsub = load(inputfile)
    G = networkx.DiGraph()
    for w1, comb_anc in optsub.items():
        print("{}: {}".format(w1, comb_anc))
        if len(comb_anc) == 0:
            raise ValueError("No optimal substemma for {}".format(w1))
        elif len(comb_anc) == 1:
            # Simple case
            nodes, edges = nodes_and_edges(w1, comb_anc[0], optsub)
            G.add_nodes_from(nodes)
            for pri, post in edges:
                G.add_edge(pri, post)
        else:
            # Complex case - multiple alternatives
            all_edges = []
            for comb in comb_anc:
                nodes, edges = nodes_and_edges(w1, comb, optsub)
                G.add_nodes_from(nodes)
                all_edges.append(edges)

            common = set.intersection(*all_edges)
            for pri, post in common:
                G.add_edge(pri, post)
            for alternative in all_edges:
                for pri, post in alternative:
                    if (pri, post) in common:
                        continue
                    G.add_edge(pri, post, style='dashed')

    print("Creating graph with {} nodes and {} edges".format(G.number_of_nodes(),
                                                             G.number_of_edges()))
    with NamedTemporaryFile() as dotfile:
        networkx.write_dot(G, dotfile.name)
        subprocess.check_call(['dot', '-Tsvg', dotfile.name, '-o', output_file])

    print("Written diagram to {}".format(output_file))
