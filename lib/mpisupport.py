"""
OpenMPI support wrapper
"""

import threading
import queue
import logging
import time
import resource
from pympler.tracker import SummaryTracker


logger = logging.getLogger()

try:
    from mpi4py import MPI
except ImportError:
    logger.warning("MPI support unavailable")


def is_parent():
    return MPI.COMM_WORLD.Get_rank() == 0


class MpiParent(object):
    mpicomm = None
    mpi_queue = queue.Queue()
    mpi_child_threads = []
    mpi_child_status = {}
    mpi_child_meminfo = {}

    # WARNING - this operates as a singleton class - always using the
    # latest instance created.
    latest_instance = None

    def __init__(self):
        logger.debug("Initialising MpiParent")
        self.__class__.latest_instance = self
        self.mpi_run()

    @classmethod
    def mpi_wait(cls, *, stop=True):
        """
        Wait for all work to be done, then tell things to stop.

        Make sure you've put things in the queue before calling this... or
        it will all just exit and move on.
        """
        if cls.mpicomm is None:
            # We haven't launched any MPI workers - we need to launch the local
            # management threads, so that the remote MPI processes will quit.
            cls.mpi_run()

        # When the queue is done, we can continue.
        logger.debug("MPI: Waiting for work to finish")
        # This waits for an empty queue AND task_done to have been called
        # for each item.
        cls.mpi_queue.join()

        if not stop:
            # Nothing more to do for now
            return

        logger.debug("MPI: Telling children to exit")
        for t in cls.mpi_child_threads:
            cls.mpi_queue.put(None)

        # Clean up the threads, in case we run out
        logger.debug("MPI: Waiting for threads to exit")
        running_threads = [t for t in cls.mpi_child_threads]
        while running_threads:
            t = running_threads.pop(0)
            t.join(0.1)
            if t.is_alive():
                running_threads.append(t)
            else:
                logger.debug("Thread {} joined - waiting for {} more"
                             .format(t, len(running_threads)))

        # Set the list as empty, so it'll be re-made if more work is required.
        cls.mpi_child_threads = []

        logger.debug("MPI: Work done")
        # We need to let threads, remote MPI processes etc. all clean up
        # properly - and a second seems to be ample time for this.
        time.sleep(1)

    @classmethod
    def show_stats(cls):
        all_stats = '\n\t'.join(['{} ({}): {}'.format(k, cls.mpi_child_meminfo.get(k, "-"),
                                                      cls.mpi_child_status[k])
                                 for k in sorted(cls.mpi_child_status.keys())])
        logger.debug("Status:\n\t{}".format(all_stats))

    @classmethod
    def mpi_manage_child(cls, child):
        """
        Manage communications with the specified MPI child
        """
        logger.info("Child manager {} starting".format(child))

        def stat(child, status, meminfo=None):
            cls.mpi_child_status[child] = "[{}]: {}".format(time.ctime(), status)
            if meminfo:
                cls.mpi_child_meminfo[child] = meminfo
            logger.debug("Child {}: {}".format(child, status))

        while True:
            # wait for something to do
            stat(child, "waiting for queue")
            args = cls.mpi_queue.get()

            # send it to the remote child
            stat(child, "sending data to child")
            cls.mpicomm.send(args, dest=child)
            if args is None:
                # That's the call to quit
                stat(child, "quitting")
                return

            stat(child, "waiting for results ({})".format(args))

            # get the results back
            while not cls.mpicomm.Iprobe(source=child):
                # FIXME - after too long we should abort this child job...
                time.sleep(1)

            ret, meminfo = cls.mpicomm.recv(source=child)
            stat(child, "sent results back", meminfo)

            # process the result by handing it to the latest_instance's
            # mpi_handle_result method.
            cls.latest_instance.mpi_handle_result(args, ret)

            cls.mpi_queue.task_done()
            stat(child, "task done")

    def mpi_handle_result(self, args, ret):
        """
        Handle an MPI result
        @param args: original args sent to the child
        @param ret: response from the child
        """
        raise NotImplemented

    @classmethod
    def mpi_run(cls):
        """
        Top-level MPI parent method.
        """
        cls.mpicomm = MPI.COMM_WORLD
        rank = cls.mpicomm.Get_rank()
        assert rank == 0
        # parent
        if cls.mpi_child_threads:
            logger.debug("We've already got child processes - so just using them")
            return

        logger.info("MPI-enabled version with {} processors available"
                    .format(cls.mpicomm.size))
        assert cls.mpicomm.size > 1, "Please run this under MPI with more than one processor"
        for child in range(1, cls.mpicomm.size):
            t = threading.Thread(target=cls.mpi_manage_child,
                                 args=(child, ),
                                 daemon=True)
            t.start()
            cls.mpi_child_threads.append(t)

        t = threading.Thread(target=cls.stats_thread,
                             daemon=True)
        t.start()

    @classmethod
    def stats_thread(cls):
        while True:
            cls.show_stats()
            time.sleep(60)


def mpi_child(fn):
    """
    An MPI child wrapper that will call the supplied function in a child
    context - reading its arguments from mpicomm.recv(source=0).
    """
    rank = MPI.COMM_WORLD.Get_rank()
    logger.debug("Child {} (remote) starting".format(rank))
    tracker = SummaryTracker()
    while True:
        # child - wait to be given a data structure
        while not MPI.COMM_WORLD.Iprobe(source=0):
            time.sleep(1)

        try:
            args = MPI.COMM_WORLD.recv(source=0)
        except EOFError:
            logger.exception("Error receiving instructions - carrying on")
            continue

        if args is None:
            logger.info("Child {} (remote) exiting - no args received".format(rank))
            break

        logger.debug("Child {} (remote) received data".format(rank))
        ret = fn(*args)

        mem_raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        mem_size = resource.getpagesize()
        mem_bytes = mem_raw * mem_size
        meminfo = "{:.2f} MB".format(mem_bytes / 1024 ** 2)

        if ret is None:
            # Nothing was generated
            MPI.COMM_WORLD.send((None, meminfo), dest=0)
            logger.info("Child {} (remote) aborted job".format(rank))
        else:
            logger.debug("Child {} (remote) sending results back".format(rank))
            MPI.COMM_WORLD.send((ret, meminfo), dest=0)
            logger.debug("Child {} (remote) completed job".format(rank))

        # Show leaking objects... uncomment this to track them...
        # tracker.print_diff()
