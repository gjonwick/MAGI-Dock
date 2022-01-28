""" Maintain the logging added functionality in one location. Each decorator
can easily applied anywhere we want it. """

import logging
from src.log.Logger import LoggerFactory

loggerFactory = LoggerFactory()


class debug_logger_class(object):

    def __init__(self, msg):
        self.msg = msg

    def __call__(self, f):
        """
        If there are decorator arguments, __call__() is only called
        once, as part of the decoration process! You can only give
        it a single argument, which is the function object.
        """
        def wrapper(*args, **kwargs):
            f(*args, *kwargs)
            print(self.msg)

        return wrapper


def debug_logger(func):
    logger = loggerFactory.giff_me_file_logger(name=func.__name__, level=logging.DEBUG)

    def wrapper(*args, **kwargs):
        logger.debug(f'Running {func.__name__} with arguments {args} and {kwargs} ... ')
        return func(*args, *kwargs)

    return wrapper
