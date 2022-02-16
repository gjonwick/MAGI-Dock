""" This is the interface of our Adapters, into what will they be adapted to. Actually, LoggingModule will just stay
abstract, there is no 'real' or 'concrete' object that is of type LoggingModule.

This is the interface used by the system (CommandWrapper). """


class LoggingModule:
    # NOTE: init method which was used to init the message_dispatcher (a signal or a logger), is removed from here.

    def log(self, msg): ...


""" Since our CommandWrapper will be expecting some object that will log by just calling the log method, all our object
 types that are able to log, print, emit, etc. should implement this interface. Therefore Adapters for Signals and
 Loggers will be created. """


class SignalAdapter(LoggingModule):

    def __init__(self, signal):
        self.signal = signal

    def log(self, msg):
        self.signal.emit(msg)


class LoggerAdapter(LoggingModule):

    def __init__(self, logger, level=None):
        self.logger = logger
        self.level = level

    def log(self, msg):
        self.logger.info(msg)
