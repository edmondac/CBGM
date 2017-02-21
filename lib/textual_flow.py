# encoding: utf-8

import subprocess
import sqlite3
import logging
import networkx
import string
import os
from .shared import OL_PARENT
from .genealogical_coherence import GenealogicalCoherence
from . import mpisupport

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

logger = logging.getLogger(__name__)


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


def mpi_child_wrapper(*args):
    """
    Wraps MPI child calls and executes the appropriate function.
    """
    key = args[0]
    if key == "GENCOH":
        return (key, generate_genealogical_coherence(*args[1:]))
    elif key == "PARENTS":
        return (key, get_parents(*args[1:]))
    else:
        raise KeyError("Unknown MPI child key: {}".format(key))


class MpiHandler(mpisupport.MpiParent):
    mpi_child_timeout = 3600 * 4  # 4 hours

    def __init__(self):
        super().__init__()
        self.textual_flow_objects = {}

    def queue_textual_flow(self, vu, **kwargs):
        """
        Make a TextualFlow object, and get it to queue up all its MPI work.
        """
        tf = TextualFlow(variant_unit=vu, **kwargs, mpihandler=self)
        self.textual_flow_objects[vu] = tf
        tf.calculate_textual_flow()

    def done(self, vu):
        """
        Finished with this VU - so lose the reference and let python free
        up some memory.
        """
        del self.textual_flow_objects[vu]

    def mpi_handle_result(self, args, ret):
        """
        Handle an MPI result
        @param args: original args sent to the child
        @param ret: response from the child
        """
        key = ret[0]
        if key == "GENCOH":
            # There's nothing to do for genealogical coherence, since the point
            # is just to store it in a cache - and the child did that.
            assert ret[1] is True, ret
        elif key == "PARENTS":
            # WARNING: We assume the first argument to get_parents is variant_unit
            tf = self.textual_flow_objects[args[1]]
            tf.mpi_result(args[1:], ret[1])
        else:
            raise KeyError("Unknown MPI child key: {}".format(key))


def generate_genealogical_coherence(w1, db_file):
    """
    Generate genealogical coherence (variant unit independent)
    and store a cached copy.
    """
    coh = GenealogicalCoherence(db_file, w1, pretty_p=False)
    if coh.check_cache():
        logger.info("Found cached genealogical coherence for {}".format(w1))
    else:
        logger.info("Calculating genealogical coherence for {}".format(w1))
        coh.generate()
        coh.store_cache()

    # A return of None is interpreted as abort, so just return True
    return True


def get_parents(variant_unit, w1, w1_reading, w1_parent, connectivity, db_file):
    """
    Calculate the best parents for this witness at this variant unit

    Return a map of connectivity value to parent map.

    WARNING: The first argument must be variant_unit, as this is a shared
             secret with MpiHandler's mpi_handle_result method.

    WARNING: The second argument must be w1, as this is a shared secret with
             TextualFlow's mpi_result method.

    This can take a long time...
    """
    logger.info("Getting best parent(s) for {}".format(w1))

    logger.debug("Calculating genealogical coherence for {} at {}".format(w1, variant_unit))
    coh = GenealogicalCoherence(db_file, w1, pretty_p=False)
    coh.load_cache()
    coh.set_variant_unit(variant_unit)
    coh.generate()

    logger.debug("Searching parent combinations")
    # we might need multiple parents if a reading requires it
    best_parents_by_rank = []
    best_rank = None
    best_parents_by_gen = []
    best_gen = None
    parents = []
    max_acceptable_gen = 2  # only allow my reading or my parent's
    parent_maps = {}
    for conn_value in connectivity:
        logger.debug("Calculating for conn={}".format(conn_value))
        try:
            combinations = coh.parent_combinations(w1_reading, w1_parent, conn_value)
        except Exception:
            logger.exception("Couldn't get parent combinations for {}, {}, {}"
                             .format(w1_reading, w1_parent, conn_value))
            parent_maps[conn_value] = None
            continue

        total = len(combinations)
        report = int(total // 10)
        for i, combination in enumerate(combinations):
            count = i + 1
            if (report and not count % report) or count == total:
                # Report every 10% and at the end
                logger.debug("Done {} of {} ({:.2f}%)".format(count, total, (count / total) * 100.0))

            if not combination:
                # Couldn't find anything to explain it
                logger.info("Couldn't find any parent combination for {}".format(w1_reading))
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

        logger.debug("Analysing results")

        if best_gen == 1:
            # We can do this with direct parents - use them
            parents = best_parents_by_gen
        else:
            # Got to use ancestors, so use the best by rank
            parents = best_parents_by_rank

        if w1_parent == OL_PARENT and not parents:
            # Top level in an overlapping unit with an omission in the initial text
            parents = [('OL_PARENT', -1, 1)]

        logger.info("Found best parents for {} (conn={}): {}".format(w1, conn_value, parents))
        parent_maps[conn_value] = parents

    return parent_maps


def textual_flow(db_file, variant_units, connectivity, perfect_only=False, suffix='', force_serial=False):
    """
    Create a textual flow diagram for the specified variant units. This will
    work out if we're using MPI and act accordingly...

    If you specify a single variant unit, and don't use MPI... then the output
    files dict will be returned. Otherwise None.
    """
    if 'OMPI_COMM_WORLD_SIZE' in os.environ and not force_serial:
        # We have been run with mpiexec
        mpi_parent = mpisupport.is_parent()
        mpi_mode = True
    else:
        mpi_mode = False

    if mpi_mode:
        if mpi_parent:
            mpihandler = MpiHandler()
        else:
            # MPI child
            mpisupport.mpi_child(mpi_child_wrapper)
            return "MPI child"

    # First generate genealogical coherence cache
    sql = "SELECT DISTINCT(witness) FROM cbgm"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    witnesses = [x[0] for x in list(cursor.execute(sql))]
    for i, w1 in enumerate(witnesses):
        if mpi_mode:
            mpihandler.mpi_queue.put(("GENCOH", w1, db_file))
        else:
            logger.debug("Generating genealogical coherence for W1={} ({}/{})".format(w1, i, len(witnesses)))
            generate_genealogical_coherence(w1, db_file)

    if mpi_mode:
        # Wait for the queue, but leave the remote children running
        mpihandler.mpi_wait(stop=False)

    # Now make textual flow diagrams
    if mpi_mode:
        if mpi_parent:
            for i, vu in enumerate(variant_units):
                logger.debug("Running for variant unit {} ({} of {})"
                             .format(vu, i + 1, len(variant_units)))
                mpihandler.queue_textual_flow(vu, db_file=db_file,
                                              connectivity=connectivity,
                                              perfect_only=False, suffix='')

            return mpihandler.mpi_wait(stop=True)
        else:
            # MPI child - nothing to do as the children are already running
            pass

    else:
        for i, vu in enumerate(variant_units):
            logger.debug("Running for variant unit {} ({} of {})"
                         .format(vu, i + 1, len(variant_units)))
            t = TextualFlow(db_file, vu, connectivity, perfect_only=False, suffix='')
            t.calculate_textual_flow()

        if len(variant_units) == 1:
            return t.output_files

    return None


class TextualFlow(object):
    def __init__(self, db_file, variant_unit, connectivity, perfect_only=False, suffix='', mpihandler=None):
        assert type(connectivity) == list, "Connectivity must be a list"
        # Fast abort if it already exists
        self.output_files = {}
        self.connectivity = []
        for conn_value in connectivity:
            dirname = "c{}".format(conn_value)
            if not os.path.exists(dirname):
                os.mkdir(dirname)
            output_file = os.path.join(os.getcwd(), dirname, "textual_flow_{}_c{}{}".format(
                variant_unit.replace('/', '_'), conn_value, suffix))

            if os.path.exists(output_file):
                logger.info("Textual flow diagram for {} already exists ({}) - skipping"
                            .format(variant_unit, output_file))
                continue

            self.output_files[conn_value] = output_file
            self.connectivity.append(conn_value)

        if not self.output_files:
            logger.info("Nothing to do - skipping variant unit {}".format(variant_unit))
            return

        self.mpihandler = mpihandler
        self.db_file = db_file
        self.variant_unit = variant_unit
        self.perfect_only = perfect_only
        self.suffix = suffix
        self.parent_maps = {}

    def calculate_textual_flow(self):
        """
        Create a textual flow diagram for the specified variant unit.

        Because I put the whole textual flow in one diagram (unlike Munster who
        show a textual flow diagram for a single reading) there can be multiple
        ancestors for a witness...
        """
        logger.info("Creating textual flow diagram for {}".format(self.variant_unit))
        logger.info("Setting connectivity to {}".format(self.connectivity))
        if self.perfect_only:
            logger.info("Insisting on perfect coherence...")

        sql = """SELECT witness, label, parent
                 FROM cbgm
                 WHERE variant_unit = \"{}\"
                 """.format(self.variant_unit)
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        data = list(cursor.execute(sql))
        # get the colour for the first char of the label (e.g. for b1 just get b)
        witnesses = [(x[0], {'color': darken(COLOURMAP.get(x[1][0], '#cccccc')),
                             'fillcolor': COLOURMAP.get(x[1][0], '#cccccc'),
                             'style': 'filled'})  # See http://www.graphviz.org/
                     for x in data]

        # 1. Calculate the best parent for each witness
        for i, (w1, w1_reading, w1_parent) in enumerate(data):
            if self.mpihandler:
                self.mpihandler.mpi_queue.put(("PARENTS", self.variant_unit, w1,
                                              w1_reading, w1_parent,
                                              self.connectivity, self.db_file))
            else:
                logger.debug("Calculating parents {}/{}".format(i, len(data)))
                parent_maps = get_parents(self.variant_unit, w1, w1_reading, w1_parent,
                                          self.connectivity, self.db_file)
                self.parent_maps[w1] = parent_maps  # a parent map per connectivity setting

        if self.mpihandler:
            # Wait a little for stabilisation
            logger.debug("Waiting for remote tasks")
            self.mpihandler.mpi_wait(stop=False)
            logger.debug("Remote tasks complete")

        # Now self.parent_maps should be complete
        logger.debug("Parent maps are: {}".format(self.parent_maps))

        # 2. Draw the diagrams
        for conn_value in self.connectivity:
            self.draw_diagram(conn_value, data, witnesses)

        if self.mpihandler:
            self.mpihandler.done(self.variant_unit)

    def draw_diagram(self, conn_value, data, witnesses):
        """
        Draw the textual flow diagram for the specified connectivity value
        """
        G = networkx.DiGraph()
        G.add_nodes_from(witnesses)
        rank_mapping = {}
        for w1, w1_reading, w1_parent in data:
            parents = self.parent_maps[w1][conn_value]
            if parents is None:
                # Couldn't calculate them
                parents = []

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

                logger.warning("{} has no parents".format(w1))
                continue

            for i, p in enumerate(parents):
                G.add_edge(p[0], w1)

        # Relable nodes to include the rank
        networkx.relabel_nodes(G, rank_mapping, copy=False)

        logger.info("Creating graph with {} nodes and {} edges".format(G.number_of_nodes(),
                                                                       G.number_of_edges()))
        # Keep the dotfile so we can change the look and feel later if we want
        dotfile = "{}.dot".format(self.output_files[conn_value])
        svgfile = "{}.svg".format(self.output_files[conn_value])
        networkx.write_dot(G, dotfile)
        subprocess.check_call(['dot', '-Tsvg', dotfile], stdout=open(svgfile, 'w'))
        logger.info("Written to {} and {}".format(dotfile, svgfile))

    def mpi_result(self, args, ret):
        """
        Handle an MPI result
        @param args: original args sent to get_parents
        @param ret: response from the child
        """
        # WARNING: We assume the second argument to get_parents is W1
        w1 = args[1]
        self.parent_maps[w1] = ret  # a parent map per connectivity setting
