""" This is the interface of our Adapters, into what will they be adapted to. Actually, LoggingModule will just stay
abstract, there is no 'real' or 'concrete' object that is of type LoggingModule.

This is the interface used by the system (CommandWrapper). """


class LoggingModule: # our "duck"

    def __init__(self, message_dispatcher):
        self.message_dispatcher = message_dispatcher

    def log(self, msg): ...


""" Since our CommandWrapper will be expecting some object that will log by just calling the log method, all our object
 types that are able to log, print, emit, etc. should implement this interface. Therefore Adapters for Signals and
 Loggers will be created. """


class SignalAdapter(LoggingModule): # our "Turkeys" (Turkey)

    def __init__(self, signal):
        super(SignalAdapter, self).__init__(signal)

    def log(self, msg):
        self.message_dispatcher.emit(msg)


class LoggerAdapter(LoggingModule): # (Ostrich)

    def __init__(self, logger, level=None):
        super(LoggerAdapter, self).__init__(logger)
        self.level = level

    def log(self, msg):
        self.message_dispatcher.info(msg)
