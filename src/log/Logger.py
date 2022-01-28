import logging


class CustomWidgetLoggingHandler(logging.Handler):

    def __init__(self, logBox) -> None:
        super().__init__()
        self.widget = logBox
        self.widget.setReadOnly(True)

    def emit(self, record):
        msg = self.format(record)
        self.widget.appendPlainText(msg)

    def write(self, m):
        pass


class LoggerFactory:

    def __init__(self, formatter='%(name)s - %(levelname)s - %(message)s'):
        self.formatter = formatter

    def giff_me_file_logger(self, **kwargs):
        logger = logging.getLogger(kwargs.pop('name'))
        logger.setLevel(kwargs.pop('level'))
        self._clear_handlers(logger)
        file_handler = logging.FileHandler('testing_logs.log')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter('%(levelname)s:%(name)s:%(message)s'))

        logger.addHandler(file_handler)

        return logger

    def giff_me_logger(self, **kwargs):
        name = kwargs.pop('name', False)
        level = kwargs.pop('level', False)
        destination = kwargs.pop('destination', False)
        logger = logging.getLogger(name)
        logger.setLevel(level)
        self._clear_handlers(logger)

        log_handler = self._get_handler(destination)
        logger.addHandler(log_handler)

        return logger

    """NOTE: since currently new instances of Ligand and Receptors controllers are created for each action on ligands 
    or receptors, giff_me_logger is called multiple times, each time adding a handler to the logger with the same 
    name (probably a logger is saved somewhere in the cache during runtime and is accessed multiple times attaching a 
    new handler to it, thus logging n+1 times. This method make sure to clear all previous handlers. """
    #  TODO: find a better way to handle this.
    def _clear_handlers(self, logger):
        for h in logger.handlers:
            logger.removeHandler(h)

    def _get_handler(self, destination):
        log_handler = CustomWidgetLoggingHandler(destination)
        log_handler.setFormatter(logging.Formatter(self.formatter))

        return log_handler
