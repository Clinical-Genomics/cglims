# -*- coding: utf-8 -*-
import logging
import coloredlogs


def init_log(logger, loglevel='WARNING'):
    """Initializes the log file in the proper format.
    Arguments:
        filename (str): Path to a file. Or None if logging is to
                         be disabled.
        loglevel (str): Determines the level of the log output.
    """
    if loglevel:
        logger.setLevel(getattr(logging, loglevel))
        coloredlogs.install(level=loglevel)

    # be more strict about logging from requests package ;)
    logging.getLogger('requests').setLevel(logging.WARNING)
