from abc import abstractmethod
from src.log.Logger import LoggerFactory


class BaseController:

    def __init__(self, form, callbacks):
        self.form = form
        self.callbacks = callbacks
        self.loggerFactory = LoggerFactory()
        self.logger = self._get_logger()

    @abstractmethod
    def _get_logger(self): ...

    @abstractmethod
    def run(self): ...
