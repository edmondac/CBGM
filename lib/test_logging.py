"""
Simple logging for unit testing
"""

import logging
import sys
import tempfile

LOGGING_CONFIGURED = False


def default_logging():
    """
    Simple logging for testing. It can be called multiple times, but
    only acts the first time.

    Warnings and above to stderr
    Everything to a debug log file
    """
    global LOGGING_CONFIGURED
    if LOGGING_CONFIGURED is True:
        return

    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.DEBUG)

    stderr_handler = logging.StreamHandler(sys.stderr)
    if '-v' in sys.argv:
        stderr_handler.setLevel(logging.DEBUG)
    else:
        stderr_handler.setLevel(logging.WARNING)
    formatter = logging.Formatter('[%(levelname)s] [%(filename)s:%(lineno)s] %(message)s')
    stderr_handler.setFormatter(formatter)
    rootLogger.addHandler(stderr_handler)

    debug_log = tempfile.mkstemp('.log')[1]
    file_handler = logging.FileHandler(debug_log)
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(asctime)s] [%(process)s] [%(filename)s:%(lineno)s] [%(levelname)s] %(message)s')
    file_handler.setFormatter(formatter)
    rootLogger.addHandler(file_handler)

    rootLogger.warning("See debug log %s", debug_log)

    LOGGING_CONFIGURED = True