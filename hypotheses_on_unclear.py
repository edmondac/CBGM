import os
import sys
import tempfile
import webbrowser
from copy import deepcopy
from itertools import product
from collections import defaultdict
from populate_db import UNCL, INIT, populate, Reading, LacunaReading, parse_input_file
from variant_units import textual_flow


def single_hypothesis(stemmata, all_mss, vu, unique_ref, force=False, perfect_only=True,
                      connectivity=499):
    """
    Generate the textual flow diagram for this variant unit in this set of stemmata
    """
    # 1. Populate the db
    db = '{}_{}.db'.format(vu.replace('/', '.'), unique_ref)
    populate(stemmata, all_mss, db, force)

    # 2. Make the textual flow diagram
    png = '{}_{}.png'.format(vu.replace('/', '.'), unique_ref)
    textual_flow(db, vu, png, connectivity, perfect_only)
    return png


def hypotheses(data, all_mss, vu, out_f, force=False, perfect_only=True, connectivity=499):
    """
    Take a variant unit and create an html page with textual flow diagrams for all
    potential hypotheses for UNCL readings.
    """
    working_dir = tempfile.mkdtemp()
    os.chdir(working_dir)
    v, u = vu.split('/')
    readings = data[v][u]
    unclear = [x for x in readings if x.parent == UNCL]
    initial_text = [x for x in readings if x.parent == INIT]
    changes = find_permutations(unclear,
                                [x.label for x in readings],
                                not initial_text)

    # 'changes' is a list of tuples, each one corresponding to a single
    # set of changes to make to the data.
    unique = 0
    results = []
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

        my_stemmata = deepcopy(data)
        my_stemmata[v][u] = new_readings
        try:
            png = single_hypothesis(my_stemmata, all_mss, vu, unique, force,
                                    perfect_only, connectivity)
        except Exception as e:
            raise
            print "ERROR doing {}, {}".format(ch, e)
            results.append((', '.join(desc), e))
        else:
            results.append((', '.join(desc), png))

        unique += 1

    html = "<html><h1>Hypotheses for {} (connectivity={})</h1>".format(vu, connectivity)
    if perfect_only:
        html += "<p>Only showing perfect coherence - forests are hidden</p>"
    for desc, png in results:
        if 'png' in png:
            html += ('<h2>{}</h2><img width="500px" src="{}" alt="{}"/><br/><hr/>\n'
                     .format(desc, png, png))
        else:
            html += ('<h2>{}</h2><p>ERROR: {}</p><hr/>\n'
                     .format(desc, png))
    html += "</html>"

    with open(out_f, 'w') as fh:
        fh.write(html)

    print "Opening browser..."
    webbrowser.open(os.path.join(working_dir, out_f))

    print "View the files in {}/{}".format(working_dir, out_f)


def find_permutations(unclear, potential_parents, can_designate_initial_text):
    """
    Find all possible permutations of unclear elements
    """
    # Every reading is a potential parent
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


def combo_recurse(readings, potential_parents, excluded_potential_parents=defaultdict(list)):
    """
    Loop through a list of readings making a list of all the possible
    changes that could be made.
    """
    options = []
    for reading in readings:
        others = [x for x in readings if x != reading]
        for change in potential_parents[reading]:
            if change in excluded_potential_parents[reading.label]:
                continue
            excluded_potential_parents[change] = reading.label
            options.append(((reading.label, change),
                             combo_recurse(others,
                                           potential_parents,
                                           excluded_potential_parents)))

    return options

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Make textual flow diagrams for hypotheses")
    parser.add_argument('inputfile', help='file containing variant reading definitions')
    parser.add_argument('-v', '--variant-unit', default=None, required=True,
                        help="Show extra data about this variant unit (e.g. 1/2-8)")
    parser.add_argument('-o', '--output-file', metavar='FILENAME',
                        default='hypothesis.html', help='write to this HTML file')
    parser.add_argument('--force', default=False, action='store_true',
                        help='force mode - overwrite any files that get in the way')
    parser.add_argument('-p', '--perfect', default=False, action='store_true',
                        help='perfect coherence - reject forests')
    parser.add_argument('-c', '--connectivity', default=499, metavar='N', type=int,
                        help='Maximum allowed connectivity in a textual flow diagram')

    args = parser.parse_args()
    if os.path.exists(args.output_file) and not args.force:
        print "{} already exists - aborting".format(args.output_file)
        sys.exit(1)

    struct, all_mss = parse_input_file(args.inputfile)
    hypotheses(struct, all_mss, args.variant_unit,
               args.output_file, args.force, args.perfect,
               args.connectivity)
