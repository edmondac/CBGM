"""
OpenMPI support wrapper
"""

import threading
import queue

try:
    from mpi4py import MPI
except ImportError:
    print("WARNING: MPI support unavailable")


def is_parent():
    return MPI.COMM_WORLD.Get_rank() == 0


class MpiParent(object):
    def __init__(self):
        self.mpicomm = None
        self.mpi_queue = queue.Queue()
        self.mpi_child_threads = []
        self.mpi_run()

    def mpi_wait(self):
        """
        Wait for all work to be done, then tell things to stop
        """
        # When the queue is done, we can continue. The child threads
        # have daemon=True and will just exit.
        self.mpi_queue.join()

        for child in range(1, self.mpicomm.size):
            # Tell the remote child processes to exit
            self.mpicomm.send(None, dest=child)

    def mpi_manage_child(self, child):
        """
        Manage communications with the specified MPI child
        """
        print("Child manager {} starting".format(child))
        while True:
            # wait for something to do
            args = self.mpi_queue.get()

            # send it to the remote child
            self.mpicomm.send(args, dest=child)

            # get the results back
            ret = self.mpicomm.recv(source=child)

            # process the result
            self.mpi_handle_result(args, ret)

            self.mpi_queue.task_done()

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
        print("MPI-enabled version with {} processors available"
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
    print("Child {} starting".format(rank))
    while True:
        # child - wait to be given a data structure
        args = MPI.COMM_WORLD.recv(source=0)
        if args is None:
            print("Child {} exiting - no args received".format(rank))
            break

        print("Child {} received data".format(rank))
        ret = fn(*args)
        if ret is None:
            # Nothing was generated
            MPI.COMM_WORLD.send(None)
            print("Child {} aborted job".format(rank))
        else:
            MPI.COMM_WORLD.send(ret)
            print("Child {} completed job".format(rank))
