# encoding: utf-8

import networkx
import sqlite3
import subprocess
import re
from tempfile import NamedTemporaryFile
from .shared import INIT, OL_PARENT, UNCL, sort_mss


def _post_process_dot(dotfile):
    """
    Post-process a dot file created by networkx to make it create a prettier
    local stemma.
    """
    re_node = re.compile("[^ ]+;")
    re_edge = re.compile("[^ ]+ -> [^ ]+;")

    output = []
    with open(dotfile) as df:
        for line in df:
            if re_node.match(line.strip()):
                line = line.replace(';', ' [shape=plaintext; fontsize=12; height=0.4; width=0.4; fixedsize=true];')
            elif re_edge.match(line.strip()):
                line = line.replace(';', ' [arrowsize=0.5];')
            output.append(line)

    with open(dotfile, 'w') as w:
        w.write(''.join(output))


def local_stemma(db_file, variant_unit):
    """
    Create a local stemma for the specified variant unit.
    """
    output_file = "{}.svg".format(variant_unit.replace('/', '_'))

    G = networkx.DiGraph()

    sql = """SELECT label, parent
             FROM reading
             WHERE variant_unit = \"{}\"
             """.format(variant_unit)
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    data = list(cursor.execute(sql))
    labels = [x[0] for x in data]

    G.add_nodes_from(labels)

    added_uncl = False
    for label, parent in data:
        if parent in (INIT, OL_PARENT):
            # We don't show a separate blob for this
            pass
        elif parent == UNCL:
            if not added_uncl:
                G.add_node('?')
                added_uncl = True
            G.add_edge('?', label)
        elif parent:
            for p in parent.split('&'):
                # multiple parents are separated by '&'
                G.add_edge(p, label)
        else:
            print("WANRNING - {} has no parents".format(label))
            continue

    print("Creating graph with {} nodes and {} edges".format(G.number_of_nodes(),
                                                             G.number_of_edges()))
    with NamedTemporaryFile() as dotfile:
        networkx.write_dot(G, dotfile.name)
        _post_process_dot(dotfile.name)
        subprocess.check_call(['dot', '-Tsvg', dotfile.name, '-o', output_file])

    print("Written diagram to {}".format(output_file))

    all_mss = set([x[0] for x in cursor.execute('SELECT DISTINCT witness FROM attestation WHERE witness != "A"')])

    sql = """SELECT label, text, GROUP_CONCAT(witness)
             FROM reading, attestation
             WHERE variant_unit = \"{}\"
             AND reading.id = attestation.reading_id
             GROUP BY label
             ORDER BY label ASC
             """.format(variant_unit)

    table = ["label\ttext\twitnesses"]
    extant = set()
    for label, text, witnesses in cursor.execute(sql):
        # Ignore 'A' for local stemmata
        wits = [x for x in witnesses.split(',') if x != 'A']
        extant = extant | set(wits)
        wits = sort_mss(wits)
        wits = ', '.join(wits)
        table.append("{}\t{}\t{}".format(label, text, wits.replace('P', '𝔓')))

    if extant != all_mss:
        wits = sort_mss(list(all_mss - extant))
        wits = ', '.join(wits)
        table.append("\tlac\t{}".format(wits.replace('P', '𝔓')))

    return ('\n'.join(table))
