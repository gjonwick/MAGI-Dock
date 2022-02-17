import subprocess
import sys

from src.log.LoggingModule import LoggingModule
from pymol.Qt import QtCore


def prepare_args(*args, **kwargs):
    """ Modify arguments in a format acceptable by Popen.
    Since Popen doesnt read dictionaries ... i.e. can't read v=True, rather than -v. """
    options = []

    print(f'Preparing arguments ... ')
    # pre-process 'dict' arguments
    for option, value in kwargs.items():
        print(f'current option = {option}, value = {value}')

        if not option.startswith('-'):

            if len(option) == 1:
                option = "-{}".format(option)
            else:
                option = "--{}".format(option)

        if value is True:
            # if user inputted ighn=True, then add to arglist -ighn (works for both - and --, # e.g. -o and --output)
            options.append(option)
            continue
        elif value is False:
            raise ValueError('False value detected!')

        if option[:2] == '--':
            if isinstance(value, list):
                print(value)
                options = options + [option] + value
                print(options)
            else:
                options.append(option + '=' + str(value))  # GNU style e.g. --output="blabla.txt"
        else:
            options.extend((option, str(value)))  # POSIX style e.g. -o "blabla.txt"

    print("Returning from prepare_args with cmd = {}".format(options + list(args)))

    return options + list(args)  # append the positional arguments


class CustomCommand(object):
    command_name = None
    executable = None

    '''
    Receives default args
    '''

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.logging_module = None  # adapter
        self.p = None

    def attach_logging_module(self, logging_module: LoggingModule):
        self.logging_module = logging_module

    def process_finished(self):
        self.logging_module.log("Process finished,")
        self.p = None

    def execute(self, *args, **kwargs):
        print("SUPPLIED: *args = [{}], **kwargs = [{}]".format(args, kwargs))
        print("DEFAULT: *args = [{}], **kwargs = [{}]".format(self.args, self.kwargs))

        _args, _kwargs = self._combine_arglist(args, kwargs)

        results, p = self._run_command(*_args, **_kwargs)
        return results

    def _combine_arglist(self, args, kwargs):
        """ Combines supplied with defaults, positionals and named separately, i.e. positional with positional, named
        with named. """
        print("Combining arguments [{}] and [{}], as well as [{} and {}]".format(self.args, args, self.kwargs, kwargs))
        _args = self.args + args
        if sys.version_info < (3, 9, 0):
            _kwargs = {**self.kwargs, **kwargs}
            # _kwargs = {}
            # _kwargs.update(self.kwargs)
            # _kwargs.update(kwargs)
        else:
            _kwargs = self.kwargs | kwargs
        _kwargs.update(kwargs)

        return _args, _kwargs

    def _run_command(self, *args, **kwargs):
        # print(f'Inside _run_command; args = {args}; kwargs = {kwargs}')

        # TODO: add code to handle the case where we want to use PIPE as input (to be discussed)

        # redirect the output to subprocess.PIPE
        # kwargs.setdefault('stderr', subprocess.PIPE)
        # kwargs.setdefault('stdout', subprocess.PIPE)

        print(f'Just before buildingProcess ... ')
        try:
            p = self.buildProcess(*args, **kwargs)
            # out, err = p.communicate()  # pass if input will be used here

            stdout = []
            stderr = []

            # TODO: use an buffer as a subject, and notify the observers (controllers) on every readLine
            assert (self.logging_module is not None)
            with p.stdout:
                for line in iter(p.stdout.readline, b''):
                    stdout.append(line.decode('utf-8'))
                    self.logging_module.log(line.decode('utf-8'))

            with p.stderr:
                for line in iter(p.stderr.readline, b''):
                    stderr.append(line.decode('utf-8'))
                    print(line.decode('utf-8'))

            p.wait()

        except Exception:
            raise

        # rc = p.returncode
        rc = p.poll()
        print("Command ran: {}".format(p.args))
        return (rc, ''.join(stdout), ''.join(stderr)), p

    def buildProcess(self, *args, **kwargs):

        cmd = self._commandline(*args, **kwargs)
        # cmd = [self.command_name] + self.prepare_args(*args, **kwargs)
        print("Inside buildProcess; the command to be run: {}".format(cmd))
        try:
            p = PopenWithInput(cmd)
        except Exception as e:
            print("Error setting up the command! Check if the paths are specified correctly!")
            self.logging_module.log(str(e))
            raise

        return p

    def _commandline(self, *args, **kwargs):
        """ Unifies the command_name and the arguments as a command line Command_name is given during class (tool)
        creation in tools.py. """

        print("Inside _commandline; before preparing args!")
        command = self.command_name
        p_args = prepare_args(*args, **kwargs)

        if self.executable is not None:
            return [self.executable, command] + p_args
        return [command] + p_args

    def __call__(self, *args, **kwargs):
        """ Receives execution-time args. """

        return self.execute(*args, **kwargs)


class PopenWithInput(subprocess.Popen):

    def __init__(self, *args, **kwargs):
        self.command = args[0]
        # if self.command.endswith('.py'):
        #     args.insert(0, sys.executable)
        super(PopenWithInput, self).__init__(*args, **kwargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


# class CustomQProcess(QtCore.QProcess):
#     command_name = None
#     executable = None
#
#     def __init__(self, *args, **kwargs):
#
#         super(CustomQProcess, self).__init__()
#         self.args = args
#         self.kwargs = kwargs
#
#     def _handle_command(self, *args, **kwargs):
#         _args, _kwargs = self._combine_arglist(args, kwargs)
#         self._run_command(*_args, **_kwargs)
#
#     def _combine_arglist(self, args, kwargs):
#
#         _args = self.args + args
#         if sys.version_info < (3, 9, 0):
#             _kwargs = {**self.kwargs, **kwargs}
#         else:
#             _kwargs = self.kwargs | kwargs
#         _kwargs.update(kwargs)
#
#         return _args, _kwargs
#
#     def _run_command(self, *args, **kwargs):
#         cmd_tuple = self._commandline(*args, **kwargs)
#         cmd = cmd_tuple[0]
#         args = cmd_tuple[1]
#         self.start(cmd, args)
#
#     def _commandline(self, *args, **kwargs):
#
#         print("Inside _commandline; before preparing args!")
#         command = self.command_name
#         p_args = prepare_args(*args, **kwargs)
#         print(f'Inside _commandline; command = {[command] + p_args}')
#
#         if self.executable is not None:
#             return self.executable, p_args
#         else:
#             return command, p_args
#
#     def __call__(self, *args, **kwargs):
#         return self._handle_command(*args, **kwargs)


def create_tool(tool_name, command_name, executable=None):
    """ Here's the whole idea of the CommandWrapper; to wrap up all the argument preparation code and make it reusable
     for every tool. """

    tool_dict = {
        'command_name': command_name,
        'executable': executable
    }
    tool = type(tool_name, (CustomCommand,), tool_dict)
    return tool


# def create_qProcess_tool(tool_name, command_name, executable=None):
#     tool_dict = {
#         'command_name': command_name,
#         'executable': executable
#     }
#
#     tool = type(tool_name, (CustomQProcess,), tool_dict)
#     return tool


def clsname_from_cmdname(cmd_name):
    """ Just a helper function to get a 'good looking' class name. Removing file extensions, etc. """

    cls_name = cmd_name
    if '.' in cmd_name:
        cls_name = cmd_name.split('.')[0]
    if cls_name[-1].isdigit():
        cls_name = cls_name[:-1]

    return cls_name
