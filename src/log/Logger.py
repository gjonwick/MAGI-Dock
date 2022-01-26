import logging


class CustomLoggingHandler(logging.Handler):

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

    def giff_me_logger(self, **kwargs):
        name = kwargs.pop('name', False)
        level = kwargs.pop('level', False)
        destination = kwargs.pop('destination', False)

        log_handler = self._get_handler(destination)

        logger = logging.getLogger(name)
        logger.addHandler(log_handler)
        logger.setLevel(level)

        return logger

    def _get_handler(self, destination):
        log_handler = CustomLoggingHandler(destination)
        log_handler.setFormatter(logging.Formatter(self.formatter))

        return log_handler
