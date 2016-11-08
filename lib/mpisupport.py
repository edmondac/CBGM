"""
OpenMPI support wrapper
"""

import threading
import queue
import logging
import time

logger = logging.getLogger()

try:
    from mpi4py import MPI
except ImportError:
    logger.warning("MPI support unavailable")


def is_parent():
    return MPI.COMM_WORLD.Get_rank() == 0


class MpiParent(object):
    def __init__(self):
        self.mpicomm = None
        self.mpi_queue = queue.Queue()
        self.mpi_child_threads = []
        self.mpi_child_status = {}
        self.mpi_run()

    def mpi_wait(self):
        """
        Wait for all work to be done, then tell things to stop.

        Make sure you've put things in the queue before calling this... or
        it will all just exit and move on.
        """
        # When the queue is done, we can continue.
        logger.debug("MPI: Waiting for the queue to be empty")
        self.mpi_queue.join()

        logger.debug("MPI: Telling children to exit")
        for t in self.mpi_child_threads:
            self.mpi_queue.put(None)

        # Clean up the threads, in case we run out
        logger.debug("MPI: Waiting for threads to exit")
        running_threads = [t for t in self.mpi_child_threads]
        while running_threads:
            t = running_threads.pop(0)
            t.join(0.1)
            if t.is_alive():
                running_threads.append(t)
            else:
                logger.debug("Thread {} joined - waiting for {} more"
                             .format(t, len(running_threads)))

        logger.debug("MPI: Work done")
        # We need to let threads, remote MPI processes etc. all clean up
        # properly - and a second seems to be ample time for this.
        time.sleep(1)

    def show_stats(self):
        all_stats = '\n\t'.join(['{}: {}'.format(k, self.mpi_child_status[k])
                                 for k in sorted(self.mpi_child_status.keys())])
        logger.debug("Status:\n\t{}".format(all_stats))

    def mpi_manage_child(self, child):
        """
        Manage communications with the specified MPI child
        """
        logger.info("Child manager {} starting".format(child))

        def stat(child, status):
            self.mpi_child_status[child] = "[{}]: {}".format(time.ctime(), status)
            logger.debug("Child {}: {}".format(child, status))

        while True:
            # wait for something to do
            stat(child, "waiting for queue")
            args = self.mpi_queue.get()

            # send it to the remote child
            stat(child, "sending data to child")
            self.mpicomm.send(args, dest=child)
            if args == None:
                # That's the call to quit
                stat(child, "quitting")
                return

            stat(child, "waiting for results ({})".format(args))

            # get the results back
            while not self.mpicomm.Iprobe(source=child):
                # FIXME - after too long we should abort this child job...
                time.sleep(1)

            ret = self.mpicomm.recv(source=child)
            stat(child, "sent results back")

            # process the result
            self.mpi_handle_result(args, ret)

            self.mpi_queue.task_done()
            stat(child, "task done")

            show_stats()

    def mpi_handle_result(self, args, ret):
        """
        Handle an MPI result
        @param args: original args sent to the child
        @param ret: response from the child
        """
        raise NotImplemented

    def mpi_run(self):
        """
        Top-level MPI parent method.
        """
        self.mpicomm = MPI.COMM_WORLD
        rank = self.mpicomm.Get_rank()
        assert rank == 0
        # parent
        logger.info("MPI-enabled version with {} processors available"
                    .format(self.mpicomm.size))
        assert self.mpicomm.size > 1, "Please run this under MPI with more than one processor"
        for child in range(1, self.mpicomm.size):
            t = threading.Thread(target=self.mpi_manage_child,
                                 args=(child, ),
                                 daemon=True)
            t.start()
            self.mpi_child_threads.append(t)


def mpi_child(fn):
    """
    An MPI child wrapper that will call the supplied function in a child
    context - reading its arguments from mpicomm.recv(source=0).
    """
    rank = MPI.COMM_WORLD.Get_rank()
    logger.debug("Child {} (remote) starting".format(rank))
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
        if ret is None:
            # Nothing was generated
            MPI.COMM_WORLD.send(None, dest=0)
            logger.info("Child {} (remote) aborted job".format(rank))
        else:
            logger.debug("Child {} (remote) sending results back".format(rank))
            MPI.COMM_WORLD.send(ret, dest=0)
            logger.debug("Child {} (remote) completed job".format(rank))
