# TODO: Fill the receptor and flexible residues lists before running the generation
# TODO: Recheck the default focuses on buttons
# then the user should be able to choose between receptors and flexibles


# from __future__ import absolute_import
# from __future__ import print_function

import csv
from email.charset import add_alias
import os
import sys
import math
import json

import errno
from contextlib import contextmanager
import os
import subprocess
import logging

from pymol.cgo import *
from pymol import cmd
from pymol.vfont import plain

from abc import abstractmethod
from pymol import cmd

from pymol.Qt import QtCore

from typing import Any

# Avoid importing "expensive" modules here (e.g. scipy), since this code is
# executed on PyMOL's startup. Only import such modules inside functions.


sys.path.append(os.path.dirname(__file__))
if '.' not in sys.path:
    sys.path.append('.')

print(sys.path)
print(sys.executable)

MODULE_UNLOADED = False
WORK_DIR = os.getcwd()

# Helpers and Utils




################################################## Helpers #############################################################

def get_scores(results_path, best_pose_only=True):
    from os import listdir
    from os.path import isfile, join
    
    if results_path == None:
        return

    #results_dir = "vina_batch_result_1mrq_54VAL_all"

    if os.path.isdir(results_path):
        results_files = [f for f in listdir(results_path) if isfile(join(results_path, f))]
    else:
        f = results_path.split('/')[-1]
        results_path = "/".join(results_path.split('/')[0:-1])
        print("Results path and file = {}, {}".format(results_path, f))
        results_files = [f]

    def process_vina_result_file(f):
        #print("In file: {}".format(f))
        compound_scores = {}
    
        with open(f) as file:
            lines = file.readlines()
            model_read = False
            for line in lines:
                if line.startswith("MODEL"):
                    model = line.rstrip()
                    compound_scores[model] = {}
                    model_read = best_pose_only
                if line.startswith("REMARK VINA RESULT"):
                    compound_scores[model]["REMARK VINA RESULT"] = line.rstrip().split(':')[1].rstrip()
                if line.startswith("REMARK INTER + INTRA"):
                    compound_scores[model]["REMARK INTER + INTRA"] = float(line.rstrip().split(':')[1].rstrip())
                if line.startswith("REMARK INTER"):
                    compound_scores[model]["REMARK INTER"] = float(line.rstrip().split(':')[1].rstrip())
                if line.startswith("REMARK INTRA"):
                    compound_scores[model]["REMARK INTRA"] = float(line.rstrip().split(':')[1].rstrip())
                if line.startswith("REMARK UNBOUND"):
                    compound_scores[model]["REMARK UNBOUND"] = float(line.rstrip().split(':')[1].rstrip())
                    if model_read:
                        break
        
        # print(compound_scores)
        return compound_scores

    results_dict = {}
    #print(results_files)
    for f in results_files:
        ligand_name = f
        # taking care of backslashes - added by python when joining paths
        if "\\" in ligand_name:
            ligand_name = ligand_name.split("\\")[-1]
        ligand_name = ligand_name.split('.')[0]
        # TODO: refactor the filename manipulation
        compound_scores = process_vina_result_file(join(results_path, f))
        results_dict[ligand_name] = compound_scores
        
    return results_dict

def get_result_files(results_path, best_pose_only=True):
    """ Used if graphical loading of the results is needed. """
    pass

def format_scores(results_dict):
    data = []
    for compound, result_info in results_dict.items():
        for pose, scores in result_info.items():
            data.append([compound, pose, float(scores["REMARK VINA RESULT"][0:15].strip())])
    
    data = sorted(data, key=lambda x : x[-1])
    return data


class vec3:
    """
    A simple class to represent 3D vectors.
    """

    def __init__(self, x: float, y: float, z: float) -> None:
        self.x = x
        self.y = y
        self.z = z

    def __add__(self, v: 'vec3') -> 'vec3':
        return vec3(self.x + v.x, self.y + v.y, self.z + v.z)

    def __sub__(self, v: 'vec3') -> 'vec3':
        return vec3(self.x - v.x, self.y - v.y, self.z - v.z)

    def __mul__(self, c) -> 'vec3':
        return vec3(self.x * c, self.y * c, self.z * c)

    def dot(self, v: 'vec3') -> float:
        return self.x * v.x + self.y * v.y + self.z * v.z

    def cross(self, v: 'vec3') -> 'vec3':
        return vec3(self.y * v.z - self.z * v.y, self.z * v.x - self.x * v.z, self.x * v.y - self.y * v.x)

    def normalize(self) -> 'vec3':
        return vec3(self.x / self.length(), self.y / self.length(), self.z / self.length())

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def __truediv__(self, c) -> 'vec3':
        return vec3(self.x / c, self.y / c, self.z / c)

    def __str__(self):
        return f'({str(self.x)}, {str(self.y)}, {str(self.z)})'

    @staticmethod
    def cube(x: float) -> float:
        return x * x * x

    def unpack(self):
        """ Return a tuple representing the coords. """
        return self.x, self.y, self.z

    def toList(self):
        """ Represent the coords as a list. """
        return [self.x, self.y, self.z]


class dotdict(dict):
    """ Convenient class to represent dictionaries in a dotted format """
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def touch(filename):
    with open(filename, 'a'):
        pass

def export_csv(directory, filename, data):

    # Parse the file name
    if '.' in filename:
        filename = filename.split('.')[0] + ".csv"
    else:
        filename += ".csv"

    output_path = os.path.join(directory, filename)

    # Export   
    print("Preparing for export on {}".format(output_path))
    with open(output_path, mode='w') as f:
        f = csv.writer(f, delimiter=',', quotechar='"')
        f.writerow(['Compound', 'Pose', 'Score'])
        for row in data:
            f.writerow(row)


# TODO: maybe yield the working dir
@contextmanager
def while_in_dir(destination_dir, create=True):
    """ Convenient function to execute stuff inside a directory. Yields the success status, and the err message if
    failed """

    cwd = os.getcwd()
    try:
        os.chdir(destination_dir)
        yield True,
    except OSError as err:
        if create and err.errno == errno.ENOENT:
            os.makedirs(destination_dir)
            os.chdir(destination_dir)
            yield True,
        else:
            yield False, f"Couldn't start working in {destination_dir} dir!"
    finally:
        os.chdir(cwd)


def absolute_path(*args):
    """ Get the absolute path of a directory or file. """

    if None in args:
        return None

    return os.path.realpath(os.path.expandvars(os.path.expanduser(os.path.join(*args))))

def filename_from_absolute(absolute_path):
    split1 = absolute_path.split('/')[-1]
    if("\\" in split1):
        split1 = split1.split("\\")[-1]
    
    return split1.split('.')[0]

def execute_command(command):
    env = dict(os.environ)
    args = command.split()
    if args[0].endswith('.py'):
        args.insert(0, sys.executable)
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE, env=env)
    print(args)
    output = p.communicate()[0]
    return p.returncode, output


""" Helper code to deal with environment modules. """


def get_loaded_modules():
    m = 'LOADEDMODULES' in os.environ
    if m:
        return os.environ['LOADEDMODULES'].split(':')
    return None


def in_path(executable_name):
    import shutil
    return shutil.which(executable_name) is not None


def is_float(element) -> bool:
    try:
        float(element)
        return True
    except ValueError:
        return False


def module_loaded(module_name):
    """ Checks if a module (as in CentOS modules) is loaded. """
    # lsmod_proc = subprocess.Popen(['module list'], stdout=subprocess.PIPE)
    # gerp_proc = subprocess.Popen(['grep', module], stdin=lsmod_proc.stdout)
    # grep_proc.communicate()
    # return grep_proc.returncode == 0

    flag = False

    loaded_modules = get_loaded_modules()
    if loaded_modules is None:
        return False

    for module in loaded_modules:
        if module_name.lower() in module.lower():
            flag = True
            break

    return flag


def find_executables(path):
    execs = []
    for exe in os.listdir(path):
        full_exe_path = os.path.join(path, exe)
        if (os.access(full_exe_path, os.X_OK)) and not os.path.isdir(full_exe_path):
            execs.append(exe)

    return execs


def __init_plugin__(app=None):
    """
    Add an entry to the PyMOL "Plugin" menu
    """
    from pymol.plugins import addmenuitemqt

    addmenuitemqt('MAGI-Dock', run_plugin_gui)


########################################### Logging ####################################################################

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

    def __init__(self, formatter="%(asctime)s: %(message)s"):
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
    name (probably a logger is saved in memory during runtime and is accessed multiple times attaching a 
    new handler to it, thus logging n+1 times. This method make sure to clear all previous handlers. """

    #  TODO: find a better way to handle this.
    def _clear_handlers(self, logger):
        for h in logger.handlers:
            logger.removeHandler(h)

    def _get_handler(self, destination):
        log_handler = CustomWidgetLoggingHandler(destination)
        log_handler.setFormatter(logging.Formatter(self.formatter, "%H:%M:%S"))

        return log_handler


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


########################################## External Tools Wrapper ######################################################


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


def clsname_from_cmdname(cmd_name):
    """ Just a helper function to get a 'good looking' class name. Removing file extensions, etc. """

    cls_name = cmd_name
    if '.' in cmd_name:
        cls_name = cmd_name.split('.')[0]
    if cls_name[-1].isdigit():
        cls_name = cls_name[:-1]

    return cls_name


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

            # TODO: this is for the coder,
            #  unfortunately every wrapped command should be associated with a logging module (to be reviewed)
            try:
                assert (self.logging_module is not None)
            except AssertionError:
                raise Exception("No logging_module for command {}".format(self.command_name))

            with p.stdout:
                for line in iter(p.stdout.readline, b''):
                    stdout.append(line.decode('utf-8'))
                    self.logging_module.log(line.decode('utf-8'))

            with p.stderr:
                for line in iter(p.stderr.readline, b''):
                    stderr.append(line.decode('utf-8'))
                    self.logging_module.log(line.decode('utf-8'))
                    #print(line.decode('utf-8'))

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
            #print("Error setting up the command! Check if the paths are specified correctly!")
            self.logging_module.log("Error setting up the command! Check if the paths are specified correctly!")
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


def create_tool(tool_name, command_name, executable):
    """ Here's the whole idea of the CommandWrapper; to wrap up all the argument preparation code and make it reusable
     for every tool. """

    tool_dict = {
        'command_name': command_name,
        'executable': executable
    }
    tool = type(tool_name, (CustomCommand,), tool_dict)
    return tool


################################################ Entities ##############################################################


# NOTE: Rendering includes communication with pymol (cmd, etc.). May be decoupled from the Box class
# let the plugin handle the rendering and communication with PyMol
# the box can just return CGO objects?
class Box:
    class __Box:
        def __init__(self) -> None:
            self.center = None
            self.dim = None
            self.fill = False
            self.hidden = False

        def __str__(self):
            return f'Center {str(self.center)}); Dim {str(self.dim)}'

        def set_fill(self, state):
            self.fill = state

        def set_hidden(self, state):
            self.hidden = state

        def set_config(self, center: 'vec3', dim: 'vec3') -> None:
            self.center = center
            self.dim = dim

        def translate(self, v: 'vec3') -> None:
            self.center = self.center + v

        def extend(self, v: 'vec3') -> None:
            self.dim = self.dim + v

        def set_center(self, v: 'vec3') -> None:
            self.center = v

        def get_center(self) -> 'vec3':
            return self.center

        def set_dim(self, v: 'vec3') -> None:
            self.dim = v

        def get_dim(self) -> 'vec3':
            return self.dim

        def __showaxes(self, minX: float, minY: float, minZ: float) -> None:
            cmd.delete('axes')
            w = 0.15  # cylinder width
            l = 5.0  # cylinder length

            obj = [
                CYLINDER, minX, minY, minZ, minX + l, minY, minZ, w, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0,
                CYLINDER, minX, minY, minZ, minX, minY + l, minZ, w, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0,
                CYLINDER, minX, minY, minZ, minX, minY, minZ + l, w, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0,
                CONE, minX + l, minY, minZ, minX + 1 + l, minY, minZ, w * 1.5, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0,
                1.0,
                CONE, minX, minY + l, minZ, minX, minY + 1 + l, minZ, w * 1.5, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 1.0,
                1.0,
                CONE, minX, minY, minZ + l, minX, minY, minZ + 1 + l, w * 1.5, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0,
                1.0
            ]

            cyl_text(obj, plain, [minX + l + 1 + 0.2, minY, minZ - w], 'X', 0.1, axes=[[1, 0, 0], [0, 1, 0], [0, 0, 1]])
            cyl_text(obj, plain, [minX - w, minY + l + 1 + 0.2, minZ], 'Y', 0.1, axes=[[1, 0, 0], [0, 1, 0], [0, 0, 1]])
            cyl_text(obj, plain, [minX - w, minY, minZ + l + 1 + 0.2], 'Z', 0.1, axes=[[0, 0, 1], [0, 1, 0], [1, 0, 0]])

            cmd.load_cgo(obj, 'axes')

        # TODO: fix repeated code

        def __draw_normals(self, normal, color):
            w = 0.15  # cylinder width
            l = 5.0  # cylinder length
            n = normal[1]

            obj = [
                CYLINDER, self.center.x, self.center.y, self.center.z, self.center.x + n.x, self.center.y + n.y,
                                                                       self.center.z + n.z, w, color[0], color[1],
                color[2], color[0], color[1], color[2],
                # CONE,   minX + l, minY, minZ, minX + 1 + l, minY, minZ, w * 1.5, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0,
            ]

            cyl_text(obj, plain, [self.center.x + n.x, self.center.y + n.y, self.center.z + n.z], str(normal[0]), 0.1,
                     axes=[[1, 0, 0], [0, 1, 0], [0, 0, 1]])

            cmd.load_cgo(obj, 'normal')

        def __refresh_unfilled(self) -> None:
            center = self.center
            dim = self.dim

            # get extremes
            (minX, minY, minZ) = (center - dim / 2).unpack()
            (maxX, maxY, maxZ) = (center + dim / 2).unpack()

            box_cgo = [
                LINEWIDTH, float(2.0),

                BEGIN, LINES,
                COLOR, float(0.5), float(0.8), float(1.0),

                VERTEX, minX, minY, minZ,  # 1
                VERTEX, minX, minY, maxZ,  # 2

                VERTEX, minX, maxY, minZ,  # 3
                VERTEX, minX, maxY, maxZ,  # 4

                VERTEX, maxX, minY, minZ,  # 5
                VERTEX, maxX, minY, maxZ,  # 6

                VERTEX, maxX, maxY, minZ,  # 7
                VERTEX, maxX, maxY, maxZ,  # 8

                VERTEX, minX, minY, minZ,  # 1
                VERTEX, maxX, minY, minZ,  # 5

                VERTEX, minX, maxY, minZ,  # 3
                VERTEX, maxX, maxY, minZ,  # 7

                VERTEX, minX, maxY, maxZ,  # 4
                VERTEX, maxX, maxY, maxZ,  # 8

                VERTEX, minX, minY, maxZ,  # 2
                VERTEX, maxX, minY, maxZ,  # 6

                VERTEX, minX, minY, minZ,  # 1
                VERTEX, minX, maxY, minZ,  # 3

                VERTEX, maxX, minY, minZ,  # 5
                VERTEX, maxX, maxY, minZ,  # 7

                VERTEX, minX, minY, maxZ,  # 2
                VERTEX, minX, maxY, maxZ,  # 4

                VERTEX, maxX, minY, maxZ,  # 6
                VERTEX, maxX, maxY, maxZ,  # 8

                END
            ]

            self.__showaxes(minX, minY, minZ)
            cmd.delete('box')
            cmd.load_cgo(box_cgo, 'box')

        # TODO: normals are hardcoded, do not work if the cube is rotated
        def __refresh_filled(self, settings={}):
            # c1 = self.center - self.dim / 2
            # c2 = c1 + vec3(self.dim.x, 0, 0)
            # c3 = c2 + vec3(0, 0, self.dim.z)
            # c4 = c3 + vec3(-self.dim.x, 0, 0)
            # normal = (c2 - c1).cross((c4 - c1))
            # normal = normal.normalize()

            center = self.center
            dim = self.dim

            # get extremes
            (minX, minY, minZ) = (center - dim / 2).unpack()
            (maxX, maxY, maxZ) = (center + dim / 2).unpack()

            c1 = vec3(minX, minY, minZ)
            c2 = vec3(minX, minY, maxZ)
            c3 = vec3(minX, maxY, minZ)
            c4 = vec3(minX, maxY, maxZ)

            c5 = vec3(maxX, minY, minZ)
            c6 = vec3(maxX, minY, maxZ)
            c7 = vec3(maxX, maxY, minZ)
            c8 = vec3(maxX, maxY, maxZ)

            # normal1 = (c1.normalize() - c2.normalize()).cross(c1.normalize() - c3.normalize())
            normal1 = vec3(-1.0, 0.0, 0.0)

            # normal2 = (c5.normalize() - c6.normalize()).cross(c5.normalize() - c7.normalize())
            normal2 = vec3(1.0, 0.0, 0.0)

            # normal2 = vec3(0.0, 0.0, 1.0)
            # normal3 = (c1.normalize() - c5.normalize()).cross(c1.normalize() - c3.normalize())
            normal3 = vec3(0.0, 0.0, -1.0)

            # normal4 = (c2.normalize() - c6.normalize()).cross(c2.normalize() - c4.normalize())
            normal4 = vec3(0.0, 0.0, 1.0)
            # normal5 = (c3.normalize() - c7.normalize()).cross(c3.normalize() - c4.normalize())
            normal5 = vec3(0.0, 1.0, 0.0)
            # normal6 = (c1.normalize() - c5.normalize()).cross(c1.normalize() - c2.normalize())
            normal6 = vec3(0.0, -1.0, 0.0)

            # Render the normals
            '''
            self.__draw_normals(['n3', normal3], [0.0, 0.0, 1.0])
            self.__draw_normals(['n4', normal4], [1.0, 0.5, 0.0])
            self.__draw_normals(['n6', normal6], [1.0, 0.0, 0.0])
            self.__draw_normals(['n5', normal5], [0.2, 0.6, 0.2])
            self.__draw_normals(['n1', normal1], [0.55, 0.1, 0.6])
            self.__draw_normals(['n2', normal2], [1.0, 1.0, 1.0])
            '''

            alpha = 0.8

            box_cgo = [
                LINEWIDTH, float(2.0),

                BEGIN, TRIANGLE_STRIP,
                NORMAL, normal1.x, normal1.y, normal1.z,
                ALPHA, float(alpha),
                COLOR, float(0.55), float(0.1), float(0.60),  # purple

                VERTEX, minX, minY, minZ,  # 1
                VERTEX, minX, minY, maxZ,  # 2
                VERTEX, minX, maxY, minZ,  # 3
                VERTEX, minX, maxY, maxZ,  # 4
                END,

                BEGIN, TRIANGLE_STRIP,
                NORMAL, normal2.x, normal2.y, normal2.z,
                ALPHA, float(alpha),
                COLOR, float(1.0), float(1.0), float(0.0),  # yellow

                VERTEX, maxX, minY, minZ,  # 5
                VERTEX, maxX, minY, maxZ,  # 6
                VERTEX, maxX, maxY, minZ,  # 7
                VERTEX, maxX, maxY, maxZ,  # 8
                END,

                BEGIN, TRIANGLE_STRIP,
                NORMAL, normal3.x, normal3.y, normal3.z,
                ALPHA, float(alpha),
                COLOR, float(0.0), float(0.0), float(1.0),  # blue

                VERTEX, minX, minY, minZ,  # 1
                VERTEX, maxX, minY, minZ,  # 5
                VERTEX, minX, maxY, minZ,  # 3
                VERTEX, maxX, maxY, minZ,  # 7
                END,

                BEGIN, TRIANGLE_STRIP,
                NORMAL, normal4.x, normal4.y, normal4.z,
                ALPHA, float(alpha),
                COLOR, float(1.0), float(0.5), float(0.0),  # orange

                VERTEX, minX, maxY, maxZ,  # 4
                VERTEX, maxX, maxY, maxZ,  # 8
                VERTEX, minX, minY, maxZ,  # 2
                VERTEX, maxX, minY, maxZ,  # 6
                END,

                BEGIN, TRIANGLE_STRIP,
                NORMAL, normal5.x, normal5.y, normal5.z,
                ALPHA, float(alpha),
                COLOR, float(0.2), float(0.6), float(0.2),  # green

                VERTEX, minX, maxY, minZ,  # 3
                VERTEX, maxX, maxY, minZ,  # 7
                VERTEX, minX, maxY, maxZ,  # 4
                VERTEX, maxX, maxY, maxZ,  # 8
                END,

                BEGIN, TRIANGLE_STRIP,
                NORMAL, normal6.x, normal6.y, normal6.z,
                ALPHA, float(alpha),
                COLOR, float(1.0), float(0.0), float(0.0),  # red
                VERTEX, minX, minY, minZ,  # 1
                VERTEX, maxX, minY, minZ,  # 5
                VERTEX, minX, minY, maxZ,  # 2
                VERTEX, maxX, minY, maxZ,  # 6

                END
            ]

            self.__showaxes(minX, minY, minZ)
            cmd.delete('box')
            cmd.load_cgo(box_cgo, 'box')

        def render(self) -> None:
            if self.hidden is False and self.center is not None and self.dim is not None:
                if self.fill:
                    self.__refresh_filled()
                else:
                    self.__refresh_unfilled()

    _instance = None

    def __init__(self):
        if not Box._instance:
            Box._instance = Box.__Box()

            # Delegate Calls to the inner private class

    def __getattr__(self, name):
        return getattr(self._instance, name)


class Ligand:
   
    def __init__(self, name, pdb, onPrepared=None) -> None:
        self.name = name
        self.pdb = pdb
        self.pdbqt = None
        self.fromPymol = True
        self.prepared = False
        self.onPrepared = onPrepared

    # @property
    def isPrepared(self):
        return self.prepared

    def prepare(self):
        self.prepared = True

    def __repr__(self):
        pdbqt = 'No PDBQT' if self.pdbqt == '' else self.pdbqt
        isPrepared = 'Prepared' if self.prepared else 'Not Prepared'
        return f'Ligand(name={self.name}, pdb={self.pdb}, pdbqt={pdbqt}, status={isPrepared})'


class Receptor:

    def __init__(self, receptor_name=None, receptor_pdbqt=None, onReceptorAdded=None) -> None:
        self.selection = None
        self.name = receptor_name
        self.pdbqt_location = receptor_pdbqt
        self.rigid_pdbqt = None
        self.flex_pdbqt = None
        self.gpf = None

        self.flexible_path = None
        self.flexible_residues = {}
        self.fromPymol = True

        self.onReceptorAdded = onReceptorAdded

    def flexibleResiduesAsString(self):
        print(f'Receptor says: my location is {str(self.pdbqt_location)}')
        res_str = ''
        pid = os.path.basename(self.pdbqt_location).split('.')[0]

        # no need for this
        # if '_' in pid:
        #     pid = pid.split('_')[-1]

        chains = []
        full_res_string = ''
        for chain, contents in self.flexible_residues.items():
            residues_per_chain = []
            chain_string = "{}:{}:".format(pid, chain)
            for res in contents:
                # full_res_name = pid + ':' + chain + ':' + '_'.join(ress)
                res_string = f'{str(res.resn) + res.resi}'
                residues_per_chain.append(res_string)
            # TODO: review this, flex_receptor doesn't accept it
            full_res_string = '_'.join(residues_per_chain)
            chain_string = chain_string + full_res_string

            chains.append(chain_string)

        final_str = ','.join(chains)

        # logging.info(final_str)
        # NOTE: should return final_string
        # return full_res_string
        return final_str

    def __repr__(self):
        pdbqt_location = 'No PDBQT' if self.pdbqt_location is None else self.pdbqt_location
        rigid_pdbqt = 'No rigidPDBQT' if self.rigid_pdbqt is None else self.rigid_pdbqt
        flex_pdbqt = 'No flexPDBQT' if self.flex_pdbqt is None else self.flex_pdbqt
        return f'Receptor(name={self.name}, pdbqt={pdbqt_location}, rigid={rigid_pdbqt}, flex={flex_pdbqt})'


####################################### Controllers / Logic ############################################################


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


class BoxAPI:

    def __init__(self) -> None:
        self.boxInstance = Box()

    def fill(self):
        self.boxInstance.set_fill(True)
        self.boxInstance.render()
        # logging.info(f'BoxAPI here ...')

    def unfill(self):
        self.boxInstance.set_fill(False)
        self.boxInstance.render()

    def extend(self, x, y, z):
        self.boxInstance.extend(vec3(x, y, z))
        self.boxInstance.render()

    def move(self, x, y, z):
        self.boxInstance.translate(vec3(x, y, z))
        self.boxInstance.render()

    def set_center(self, x, y, z):
        self.boxInstance.set_center(vec3(x, y, z))
        self.boxInstance.render()
        print(self.boxInstance)

    def set_dim(self, x, y, z):
        self.boxInstance.set_dim(vec3(x, y, z))
        self.boxInstance.render()
        print(self.boxInstance)

    # TODO: Decouple generation from returning the data?

    def gen_box(self, selection="(sele)", padding=2.0) -> 'dotdict':
        ([minX, minY, minZ], [maxX, maxY, maxZ]) = cmd.get_extent(selection)
        # cmd.iterate(selector.process(selection, 'stored.residues.add(resv'))
        # for residue in stored.residues:
        #     print(str(residue))
        center = vec3((minX + maxX) / 2, (minY + maxY) / 2, (minZ + maxZ) / 2)
        dim = vec3((maxX - minX + 2 * padding), (maxY - minY + 2 * padding), (maxZ - minZ + 2 * padding))
        self.boxInstance.set_config(center, dim)
        print(self.boxInstance)
        self.boxInstance.render()
        return self.box_data()

    def read_box(self, filename) -> 'dotdict':
        with open(filename, 'r') as f:
            lines = f.readlines()

            centerX = float(lines[0].split('=')[1].strip())
            centerY = float(lines[1].split('=')[1].strip())
            centerZ = float(lines[2].split('=')[1].strip())

            dimX = float(lines[3].split('=')[1].strip())
            dimY = float(lines[4].split('=')[1].strip())
            dimZ = float(lines[5].split('=')[1].strip())

            center = vec3(centerX, centerY, centerZ)
            dim = vec3(dimX, dimY, dimZ)

        self.boxInstance.set_config(center, dim)
        print(self.boxInstance)
        self.boxInstance.render()
        return self.box_data()

    def save_box(self, filename, vinaOutput):
        box = self.boxInstance
        with open(filename, 'w') as f:
            f.write("center_x = " + str(box.center.x) + '\n')
            f.write("center_y = " + str(box.center.y) + '\n')
            f.write("center_z = " + str(box.center.z) + '\n')

            f.write("size_x = " + str(box.dim.x) + '\n')
            f.write("size_y = " + str(box.dim.y) + '\n')
            f.write("size_z = " + str(box.dim.z) + '\n')

            # if vinaOutput != '':
            #     f.write("out = " + vinaOutput + '\n')

    # TODO: handle the case when the name changes
    # Explicit function to render and hide the box (why not?)
    def render_box(self):
        self.boxInstance.render()

    def hide_box(self):
        self.boxInstance.set_hidden(True)
        cmd.delete('box')
        cmd.delete('axes')

    def show_box(self):
        self.boxInstance.set_hidden(False)
        self.boxInstance.render()

    def box_data(self) -> 'dotdict':
        box = self.boxInstance

        if not self.box_exists():
            raise Exception("No box config yet!")

        return dotdict({
            "center": dotdict({
                "x": box.center.x,
                "y": box.center.y,
                "z": box.center.z
            }),
            "dim": dotdict({
                "x": box.dim.x,
                "y": box.dim.y,
                "z": box.dim.z
            })
        })

    def box_exists(self) -> bool:
        return self.boxInstance.center is not None and self.boxInstance.dim is not None

    def is_hidden(self):
        return self.boxInstance.hidden

    def is_filled(self):
        return self.boxInstance.fill


def get_pdbqt(ligand):
    return ligand.pdbqt


class DockingJobController(BaseController):

    def __init__(self, form, multiple_ligand_docking=False, callbacks=None):
        super(DockingJobController, self).__init__(form, callbacks)
        self.multiple_ligand_docking = multiple_ligand_docking

    def _get_logger(self) -> Any:
        return self.loggerFactory \
            .giff_me_logger(name=type(self).__name__,
                            level=logging.DEBUG,
                            destination=self.form.dockingLogBox)

    def run(self):
        adContext = ADContext()
        vina = Vina()
        # make sure tools are loaded; do the check here, because there's no point of calling the thread
        # if there is no tool to perform the job (check already done when initializing Vina())

        form = self.form
        form.runDocking_btn.setEnabled(False)
        form.runMultipleDocking_btn.setEnabled(False)

        form.thread = QtCore.QThread()
        form.worker = VinaWorker(form, vina, self.multiple_ligand_docking)
        form.worker.moveToThread(form.thread)
        form.thread.started.connect(form.worker.run)
        form.worker.finished.connect(form.thread.quit)
        form.worker.finished.connect(form.worker.deleteLater)
        # form.thread.finished.connect(form.thread.deleteLater)
        form.worker.finished.connect(self.onFinished)
        form.worker.progress.connect(lambda x: self.logger.info(x))

        # start thread
        form.thread.start()

        # form.thread.finished.connect(
        #     lambda: self.logger.info('Finish!')
        # )

    def onFinished(self, msg):
        adContext = ADContext()
        self.form.runDocking_btn.setEnabled(True)
        self.form.runMultipleDocking_btn.setEnabled(True)
        self.logger.info(msg)
        self.form.vinaoutput_txt.setText(adContext.config['output_file'])
        self.form.loadResults_btn.click()


    def generateAffinityMaps(self, selectedLigands):
        """ Responsible for generating both gpf and affinity maps. """

        if len(selctedLigands) == 0:
            self.logger.error('Select a ligand first!')
            return


        adContext = ADContext()
        autoDock = AutoDock()
        receptor = adContext.receptor
        ligand_name = selectedLigands[0].text()
        ligand = adContext.ligands[ligand_name]

        if ligand.pdbqt is None:
            self.logger.error('The selected ligand is not prepared!')
            return

        if not hasattr(autoDock, "prepare_gpf") or not hasattr(autoDock, "autogrid"):
            print("Prepare gpf or autogrid was not loaded correctly! Make sure the paths are specified!")
            self.logger.error("Prepare gpf or autogrid was not loaded correctly! Make sure the paths are specified!")
            return

        autoDock.prepare_gpf.attach_logging_module(LoggerAdapter(self.logger))
        autoDock.autogrid.attach_logging_module(LoggerAdapter(self.logger))

        flex_docking = not len(receptor.flexible_residues) == 0

        if flex_docking:
            saved_receptor_name = receptor.rigid_pdbqt.split('.')[0]
        else:
            saved_receptor_name = receptor.pdbqt_location.split('.')[0]

        receptor_gpf = "{}.gpf".format(saved_receptor_name)  # full path here
        # In order for the receptor to "have" an gpf, it must be "associated" with a ligand.
        # Everytime we generate a gpf, the file is overridden "with" the new ligand. Rigid pdbqt will be used if
        # flexible docking.
        receptor_pdbqt = "{}.pdbqt".format(saved_receptor_name)  # receptor_pdbqt will be the rigid pdbqt if flexible
        receptor_pdbqt_dir = os.path.dirname(receptor_pdbqt)

        with while_in_dir(receptor_pdbqt_dir): # TODO: this cd-s to receptor pdbqt dir, which may be different than ligand dir, working_dir may be a better approach
            try:

                (rc, stdout, stderr) = autoDock.prepare_gpf(l=ligand.pdbqt, r=receptor_pdbqt, o=receptor_gpf,
                                                            y=True)
                if rc == 0:
                    receptor.gpf = receptor_gpf
                    self.logger.info("GPF for the {}_{} complex ready!".format(ligand.name, receptor.name))
                else:
                    self.logger.error("Couldn't generate GPF for the {}_{} complex!".format(ligand.name, receptor.name))
                    self.logger.error("Please make sure autodock is loaded!")
                    return

            except Exception as e:
                self.logger.error(repr(e))
                self.logger.error("An error occurred preparing gpf!")
                return

            try:
                (rc, stdout, stderr) = autoDock.autogrid(p="{}.gpf".format(saved_receptor_name),
                                                          l="{}.glg".format(saved_receptor_name))
                if rc == 0:
                    self.logger.info("Affinity maps for the {}_{} complex ready!".format(ligand.name, receptor.name))
                else:
                    self.logger.error("Could not generate affinity maps for the {}_{} complex!".format(ligand.name,
                                                                                                       receptor.name))
            except Exception as e:
                self.logger.error(str(e))
                self.logger.error("An error occurred trying to run autogrid, please check if the path is correct!")
                return


class VinaWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal(str)
    progress = QtCore.pyqtSignal(str)

    def __init__(self, form, vina, multiple_ligands=False):
        super(VinaWorker, self).__init__()
        self.form = form
        self.arg_dict = {}
        self.multiple_ligands = multiple_ligands
        self.vina = vina

    def default_args(self):
        adContext = ADContext()

        # no need to check dockingjob_params, since they have defaults
        if adContext.config['box_path'] is None: # TODO: could define some new Exceptions classes
            raise

        self.arg_dict.update(
            exhaustiveness=adContext.config['dockingjob_params']['exhaustiveness'],
            num_modes=adContext.config['dockingjob_params']['n_poses'],
            energy_range=adContext.config['dockingjob_params']['energy_range'],
            min_rmsd=adContext.config['dockingjob_params']['min_rmsd'],
            scoring=adContext.config['dockingjob_params']['scoring'],
            config=adContext.config['box_path']
        )

    def run(self):
        adContext = ADContext()
        logging_module = SignalAdapter(self.progress)

        try:
            self.default_args()
        except:
            self.finished.emit("No Docking Box configuration provided! Please specify the box coordinates first!")
            return

        if not hasattr(self.vina, "vina"):
            print("Vina was not loaded correctly! Make sure the paths are specified!")
            self.finished.emit("Vina was not loaded correctly! Make sure the paths are specified!")
            return

        self.vina.vina.attach_logging_module(logging_module)

        working_dir = adContext.config['working_dir']
        if working_dir == None:
            print("Please specify the working directory first!")
            self.finished.emit("Please specify the working directory first!")
            return

        # make sure there are ligands to dock
        ligands_to_dock = adContext.ligands_to_dock
        if len(ligands_to_dock) < 1:
            self.finished.emit('There are no ligands to dock!')
            return

        receptor = adContext.receptor
        if receptor is None:
            self.finished.emit("No receptor loaded! Please generate and load the receptor first!")
            return

        """ When distinguishing between flexible or rigid, the receptor will make the difference. In the 
        case of multiple docking, each ligand will be run on flexible residues if the receptor has flexible residues. 
        If there are ligands to be run with rigid docking, than make sure there is another receptor with rigid residues. 
        """
        with while_in_dir(working_dir):

            if len(ligands_to_dock) == 1:
                # basic docking
                ligand_to_dock = ligands_to_dock[list(ligands_to_dock.keys())[0]]

                # the case with ad4 scoring is different, handle it in a separate function
                if self.arg_dict['scoring'] == 'ad4':
                    arg_dict = self.ad_docking(ligand_to_dock, receptor)
                else:
                    # (rc, stdout, stderr) = self.basic_docking(ligand_to_dock, receptor)
                    arg_dict = self.basic_docking(ligand_to_dock, receptor)

            else:

                # batch docking
                # (rc, stdout, stderr) = self.batch_docking(ligands_to_dock, receptor)
                if self.multiple_ligands:
                    self.progress.emit('Preparing for multiple ligand docking ... ')
                    arg_dict = self.multiple_ligand_docking(ligands_to_dock, receptor)
                else:
                    self.progress.emit('Preparing for batch docking ... ')
                    arg_dict = self.batch_docking(ligands_to_dock, receptor)

            try:
                #adContext.config['output_file'] == arg_dict['out']
                # TODO: add missing affinity maps error handling
                (rc, stdout, stderr) = self.vina.vina(**arg_dict)
                self.progress.emit("return code = {}".format(rc))
                if rc == 0:
                    self.progress.emit("Success!")
                    # self.finished.emit(stdout.decode('utf-8'))
                    output_path = arg_dict['out'] if 'out' in arg_dict else arg_dict['dir']
                    adContext.config['output_file'] = os.path.join(working_dir, output_path)
                else:
                    self.progress.emit(stderr)
            except KeyError as e:
                self.progress.emit(str(e))
                self.finished.emit("An error occurred trying to run vina, please check if the path is correct!")
        
        self.finished.emit('Docking thread finished!')
        
    def ad_docking(self, ligand, receptor):
        arg_dict = self.arg_dict
        flex_docking = not len(receptor.flexible_residues) == 0
        try:
            receptor_maps_dir = os.path.dirname(receptor.gpf)
        except Exception as e:
            self.finished.emit(repr(e))
            return

        if flex_docking:
            rigid_receptor_pdbqt = receptor.rigid_pdbqt
            saved_rigid_receptor_name = filename_from_absolute(rigid_receptor_pdbqt)
            flex_receptor = receptor.flex_pdbqt
            if flex_receptor is not None and rigid_receptor_pdbqt is not None:
                output_file = "ad_vina_result_{}_{}_flexible.pdbqt".format(receptor.name, ligand.name)
                
                arg_dict.update(flex=flex_receptor,
                                ligand=ligand.pdbqt,
                                maps=saved_rigid_receptor_name,
                                out=output_file)
        else:
            saved_receptor_name = filename_from_absolute(receptor.pdbqt_location)
            print("Maps folder = {}".format(saved_receptor_name))
            output_file = "ad_vina_result_{}_{}.pdbqt".format(receptor.name, ligand.name)
            
            arg_dict.update(ligand=ligand.pdbqt,
                            maps=saved_receptor_name,
                            out=output_file)

        return arg_dict

    def basic_docking(self, ligand, receptor):
        """ Function responsible for preparing the options to run docking with only 1 ligand. """

        arg_dict = self.arg_dict
        flex_docking = not len(receptor.flexible_residues) == 0

        if flex_docking:
            rigid_receptor = receptor.rigid_pdbqt
            flex_receptor = receptor.flex_pdbqt
            if flex_receptor is not None and rigid_receptor is not None:
                output_file = "vina_result_{}_{}_flexible.pdbqt".format(receptor.name, ligand.name)
                arg_dict.update(receptor=rigid_receptor,
                                flex=flex_receptor,
                                ligand=ligand.pdbqt,
                                out=output_file)
            else:
                self.finished("When running flexible docking please generate the flexible receptor first!")
                return
        else:
            output_file = "vina_result_{}_{}.pdbqt".format(receptor.name, ligand.name)
            arg_dict.update(receptor=receptor.pdbqt_location,
                            ligand=ligand.pdbqt,
                            out=output_file)
        return arg_dict

    # TODO: vinardo and ad4 scoring functions currently do not work in batch docking
    def batch_docking(self, ligands_to_dock, receptor):
        """ Function responsible for preparing the options to run docking in batch mode. """

        arg_dict = self.arg_dict
        ligands_pdbqt = list(map(get_pdbqt, list(ligands_to_dock.values())))
        self.progress.emit(str(ligands_pdbqt))
        print(ligands_pdbqt)
        flex_docking = not len(receptor.flexible_residues) == 0

        if flex_docking:
            rigid_receptor = receptor.rigid_pdbqt
            flex_receptor = receptor.flex_pdbqt
            if flex_receptor is not None and rigid_receptor is not None:
                output_dir = "vina_batch_result_{}_flexible".format(receptor.name)
                if not os.path.isdir(output_dir):
                    os.mkdir(output_dir)
                arg_dict.update(receptor=rigid_receptor,
                                flex=flex_receptor,
                                batch=ligands_pdbqt,
                                dir=output_dir)
            else:
                self.finished("When running flexible docking please generate the flexible receptor first!")
                return
        else:
            output_dir = "vina_batch_result_{}".format(receptor.name)
            if not os.path.isdir(output_dir):
                os.mkdir(output_dir)
            arg_dict.update(receptor=receptor.pdbqt_location,
                            batch=ligands_pdbqt,
                            dir=output_dir)
        return arg_dict

    def multiple_ligand_docking(self, ligands_to_dock, receptor):

        """
        Traceback (most recent call last):
        File "/home/u3701/.pymol/startup/MAGI-Dock/src/api/DockingAPI.py", line 108, in run
            self.finished.emit(e)
        TypeError: VinaWorker.finished[str].emit(): argument 1 has unexpected type 'TypeError'

        """

        """ Function responsible for running docking with multiple ligands. """
        # self.logger.error("Multiple ligand docking not implemented yet!")

        arg_dict = self.arg_dict
        flex_docking = not len(receptor.flexible_residues) == 0
        ligands_pdbqt = list(map(get_pdbqt, list(ligands_to_dock.values())))
        self.progress.emit(str(ligands_pdbqt))

        if flex_docking:
            rigid_receptor = receptor.rigid_pdbqt
            flex_receptor = receptor.flex_pdbqt
            if flex_receptor is not None and rigid_receptor is not None:
                output_file = "vina_multidock_result_{}_flexible.pdbqt".format(receptor.name)
                arg_dict.update(receptor=rigid_receptor,
                                flex=flex_receptor,
                                ligand=ligands_pdbqt,
                                out=output_file)
            else:
                self.finished.emit("No flex and rigid parts!")
                return
        else:
            output_file = "vina_multidock_result_{}.pdbqt".format(receptor.name)
            arg_dict.update(receptor=receptor.pdbqt_location,
                            ligand=ligands_pdbqt,
                            out=output_file)

        return arg_dict


# TODO: CRUD code may be wrapped into a "DAO" object
class LigandJobController(BaseController):

    def __init__(self, form=None, callbacks=None):
        super(LigandJobController, self).__init__(form, callbacks)
        self.threadpool = QtCore.QThreadPool()
        self.adContext = ADContext()

    def run(self):
        self.logger.info('Im running fine!')
        self.prepare()

    def _get_logger(self):
        return self.loggerFactory.giff_me_logger(name=type(self).__name__, level=logging.DEBUG, destination=self.form.ligandLogBox)

    """ Load an imported ligand to the list of ligands (not prepared). """

    def load_ligand(self, ligand_path):
        adContext = self.adContext

        if ligand_path.split('.')[1] == 'pdbqt':
            self.logger.error("Ligand is already prepared, please choose another file!")
            return

        ligand_name = ligand_path.split('/')[-1].split('.')[0]

        ligand = Ligand(ligand_name, ligand_path)  # onPrepared=onPreparedLigandChange
        ligand.fromPymol = False

        try:
            adContext.addLigand(ligand)
            cmd.load(ligand_path, object=ligand_name)
        except Exception as e:
            self.logger.error("An error occurred while importing ligand!")

    def load_prepared_ligand(self, prepared_ligand_path):
        print("Loading prepared ligand with path = {}".format(prepared_ligand_path))
        adContext = self.adContext
        prepared_ligand_name = prepared_ligand_path.split('/')[-1].split('.')[0]
        extension = prepared_ligand_path.split('.')[1]
        if extension != 'pdbqt':
            self.logger.error("Please select a .pdbqt file!")
            return

        ligand = Ligand(prepared_ligand_name, None)
        ligand.pdbqt = prepared_ligand_path
        ligand.fromPymol = False
        ligand.prepared = True

        try:
            adContext.addLigand(ligand)
            cmd.load(prepared_ligand_path, object=prepared_ligand_name)
        except Exception as e:
            self.logger.error("An error occurred while importing prepared ligand!")

    def add_ligands(self, ligand_widget_list):
        """ Used to add PyMOL ligands to the ligands widget (not prepared ligands).
        Iteration on every ligand is done here. """

        if len(ligand_widget_list) == 0:
            self.logger.error(
                'Select the ligands please!'
            )
            return

        adContext = self.adContext

        for index, sele in enumerate(ligand_widget_list):
            ligand = Ligand(sele.text(), '')  # onPrepared=onPreparedLigandChange
            adContext.addLigand(ligand)

        self.logger.debug("Ligands added = {}".format(adContext.ligands))

    def remove_ligands(self, ligand_widget_list):

        if len(ligand_widget_list) == 0:
            self.logger.info(
                'Select the ligands please!'
            )
            return

        adContext = self.adContext

        for index, item in enumerate(ligand_widget_list):
            adContext.removeLigand(item.text())
            # TODO: remove foreign ligand from pymol (optional)
        adContext.signalLigandAction()

    # Ligands are prepared on a seperate thread
    def prepare_ligands(self, ligand_widget_list):
        adContext = self.adContext
        ad = AutoDock()

        # if not adContext.ad_tools_loaded:
        #     self.logger.info("AutoDock tools are not loaded correctly! Make sure the paths are specified!")
        #     return

        if len(ligand_widget_list) == 0:
            self.logger.info(
                'Select a ligand please!'
            )
            return

        worker = PreparationWorker(self.form, ligand_widget_list, ad)
        worker.signals.progress.connect(lambda x: self.logger.info(x))
        worker.signals.finished.connect(self.onFinished)
        worker.signals.success.connect(self.onSuccess)
        worker.signals.error.connect(self.onError)
        worker.signals.pdb_update.connect(self.onPDBUpdate)

        self.form.genLigands_btn.setEnabled(False)
        self.form.loadLigand_btn.setEnabled(False)
        self.form.removeLigand_btn.setEnabled(False)
        self.form.addLigand_btn.setEnabled(False)
        self.threadpool.start(worker)

    def onFinished(self, msg):
        self.form.genLigands_btn.setEnabled(True)
        self.form.loadLigand_btn.setEnabled(True)
        self.form.removeLigand_btn.setEnabled(True)
        self.form.addLigand_btn.setEnabled(True)
        self.logger.info(msg + " ===== Finished! ===== ")
        self.adContext.signalLigandAction()

    def onSuccess(self, ligand):
        ligand.prepare()
        # self.adContext.signalLigandAction()
        self.logger.info("Ligand {} pdbqt generated at {}".format(ligand.name, ligand.pdbqt))

    def onError(self, msg):
        self.logger.error(msg)

    def onPDBUpdate(self, ligand):
        try:
            cmd.save(ligand.pdb, ligand.name)
        except cmd.QuietException:
            pass


class WorkerSignals(QtCore.QObject):
    """ Class containing the signals, since we must inherit from QObject. """

    progress = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal(str)
    success = QtCore.pyqtSignal(Ligand)
    error = QtCore.pyqtSignal(str)
    progress_bar = QtCore.pyqtSignal(float)
    pdb_update = QtCore.pyqtSignal(Ligand)


class PreparationWorker(QtCore.QRunnable):
    """ Thread that deals with the actual process of ligand preparation. """
    working_dir = None

    def __init__(self, form, ligands, ad):
        super(PreparationWorker, self).__init__()
        self.form = form
        self.ligands = ligands
        self.signals = WorkerSignals()
        self.adContext = ADContext()
        self.ad = ad
        self.working_dir = self.adContext.config['working_dir']
        self.all_ligands = self.adContext.ligands
        #self._setup_logging()
        self.config = self.adContext.config['ligandjob_params']

    def _setup_logging(self):
        logging_module = SignalAdapter(self.signals.progress)
        self.ad.prepare_ligand.attach_logging_module(logging_module)

    def run(self):

        if self.working_dir == None:
            print("Please specify the working directory first!")
            self.signals.error.emit("Please specify the working directory first!")
            self.signals.finished.emit("")
            return


        # adContext = self.adContext
        if not hasattr(self.ad, 'prepare_ligand'): # TODO: if the tools loaded check is done in the prepare_ligands function, we can remove this
            print("Prepare ligand was not loaded correctly! Make sure the paths are specified!")
            self.signals.error.emit("Prepare ligand was not loaded correctly! Make sure the paths are specified!")
            self.signals.finished.emit("")
            return

        form = self.form
        ligands = self.ligands
        self._setup_logging()
        
        arg_dict = {}  # command options will be contained in this dictionary
        if form.checkBox_hydrogens.isChecked():
            arg_dict.update(A='checkhydrogens')

        for index, ligand_selection in enumerate(ligands):
            # Currently ligand_id and ligand.name are the same
            ligand_id = ligand_selection.text()
            ligand = self.all_ligands[ligand_id]
            ligand_pdb = self._update_ligand_pdb(ligand)
            # ligand_pdb = 'TEST_no_pdb_update'
            ligand_pdb_dir = os.path.dirname(ligand_pdb)
            ligand_pdbqt = os.path.join(self.working_dir, "plg_{}.pdbqt".format(ligand.name))
            ligand.pdbqt = ligand_pdbqt

            arg_dict.update(l=ligand_pdb, o=ligand_pdbqt)

            with while_in_dir(ligand_pdb_dir):  # because autodock can't see files in other directories ...

                try:
                    (rc, stdout, stderr) = self.ad.prepare_ligand(**arg_dict)
                    # (rc, stdout, stderr) = adContext.ls('-l')
                    if rc == 0:
                        self.signals.success.emit(ligand)
                    else:
                        self.signals.error.emit("An error occurred while trying to prepare {}!".format(ligand.name))
                except Exception as e:
                    s = str(e)
                    self.signals.error.emit(s)
                    self.signals.finished.emit('')

        self.signals.finished.emit('Ran all ligands!')

    def _update_ligand_pdb(self, ligand):

        if ligand.fromPymol:
            ligand_pdb = os.path.join(self.working_dir, "plg_{}.pdb".format(ligand.name))
            self.signals.progress.emit("Generating pdb {} for ligand {}".format(ligand_pdb, ligand.name))
            ligand.pdb = ligand_pdb
            self.signals.pdb_update.emit(ligand)
            # try:
            #     cmd.save(ligand.pdb, ligand.name)
            # except cmd.QuietException:
            #     pass
        else:
            ligand_pdb = ligand.pdb

        return ligand_pdb


class RigidReceptorController(BaseController):

    def __init__(self, form, callbacks=None):
        super(RigidReceptorController, self).__init__(form, callbacks)

    def _get_logger(self):
        return self.loggerFactory \
            .giff_me_logger(name=type(self).__name__,
                            level=logging.DEBUG,
                            destination=self.form.receptorLogBox)

    def run(self):
        adContext = ADContext()
        ad = AutoDock()  # tools will be loaded here, it is ok to reload them every time we "hit" run
        # all the mess with re-loading them whenever the path changed was caused because previously we would only
        # load the tools only when they were not already loaded (the if not adContext.ad_tools_loaded condition)
        # remove that
        # "Could not load AutoDock tools!" AutoDock class already takes care of that!
        arg_dict = {}

        # TODO: (future issue) remove form reference from here; better if the API classes do not know about the form
        form = self.form
        selection = form.sele_lstw.selectedItems()

        if len(selection) == 0:
            self.logger.error(
                'Select a receptor please!'
            )
            return

        if len(selection) > 1:
            print('You can only have 1 receptor!')
            self.logger.error('You can only have 1 receptor!')
            return

        receptor_name = selection[0].text()

        working_dir = adContext.config['working_dir']
        if working_dir == None:
            print("Please specify the working directory first!")
            self.logger.info("Please specify the working directory first!")
            return

        receptor_pdb = os.path.join(working_dir, f'plg_{receptor_name}.pdb')
        receptor_pdbqt = os.path.join(working_dir, f'plg_{receptor_name}.pdbqt')
        receptor_pdb_dir = os.path.dirname(receptor_pdb)

        try:
            cmd.save(receptor_pdb, receptor_name)
        except cmd.QuietException:
            pass

        if not hasattr(ad, 'prepare_receptor'):
            print("Prepare receptor was not loaded correctly! Make sure the paths are specified!")
            self.logger.error("Prepare receptor was not loaded correctly! Make sure the paths are specified!")
            return

        ad.prepare_receptor.attach_logging_module(LoggerAdapter(self.logger))
        arg_dict.update(r=receptor_pdb, o=receptor_pdbqt)

        with while_in_dir(receptor_pdb_dir):  # because autodock can't see files in other directories ...
            if form.checkBox_addHydrogens_receptor.isChecked():
                arg_dict.update(A='hydrogens')

            (rc, stdout, stderr) = ad.prepare_receptor(**arg_dict)

            if rc == 0:
                receptor = Receptor(receptor_name, receptor_pdbqt, onReceptorAdded=self.callbacks['onReceptorAdded'])
                adContext.addReceptor(receptor)
                self.logger.info(f'Receptor pdbqt generated at: {adContext.receptor.pdbqt_location}')
            else:
                self.logger.error(f'Failed generating receptor {receptor_name}!')


class FlexibleReceptorController(BaseController):

    def __init__(self, form, callbacks=None):
        super(FlexibleReceptorController, self).__init__(form, callbacks)

    def _get_logger(self):
        return self.loggerFactory.giff_me_logger(name=type(self).__name__, level=logging.DEBUG,
                                                 destination=self.form.receptorLogBox)

    def run(self):
        from pymol import stored
        """ Generates pdbqt files for the flexible receptor. """
        adContext = ADContext()
        ad = AutoDock()
        form = self.form
        sele = form.sele_lstw.selectedItems()

        if len(sele) == 0:
            self.logger.error(
                'Select an option representing flexible residues please!'
            )
            return

        if len(sele) > 1:
            print('One selection at a time please!')
            self.logger.error('One selection at a time please!')
            return

        if adContext.receptor is None:
            self.logger.error('Please generate the receptor first!')
            return

        # XXX: there was an error trying to generate only 1 flexible residue
        # TODO: encapsulate, get selected residues
        sele = sele[0].text()
        stored.flexible_residues = []
        cmd.iterate(sele + ' and name ca', 'stored.flexible_residues.append([chain, resn, resi])')
        # print(str(stored.flexible_residues))
        chains = {}
        for chain, resn, resi in stored.flexible_residues:
            if resn not in ['ALA', 'GLY', 'PRO']:
                if chain in chains:
                    chains[chain].append(dotdict({'resn': resn, 'resi': resi}))
                else:
                    chains[chain] = [dotdict({'resn': resn, 'resi': resi})]

        # TODO: encapsulate, get loaded (loaded automatically into VinaCoupler when you click on it) receptor
        if adContext.receptor is not None:
            adContext.receptor.flexible_residues = chains

            # receptor is already set, now you just reset it

        """ In the pymol session the flexible residues will have already
        been assigned to the receptor. If the program fails to generate the 
        respective (pdbqt) files, then the receptor and its flexible
        residues will still be 'cached' in the session, and ready to be rerun. """

        working_dir = adContext.config['working_dir']
        if working_dir == None:
            print("Please specify the working directory first!")
            self.logger.info("Please specify the working directory first!")
            return

        # with while_in_dir(working_dir):

        res_string = adContext.receptor.flexibleResiduesAsString()
        receptor_pdbqt = adContext.receptor.pdbqt_location
        receptor_pdbqt_dir = os.path.dirname(receptor_pdbqt)

        self.logger.info(f'Generating flexible residues ... {res_string}')

        if not hasattr(ad, 'prepare_flexreceptor'):
            print("Prepare flexreceptor was not loaded correctly! Make sure the paths are specified!")
            self.logger.error("Prepare flexreceptor was not loaded correctly! Make sure the paths are specified!")
            return

        ad.prepare_flexreceptor.attach_logging_module(LoggerAdapter(self.logger))

        with while_in_dir(receptor_pdbqt_dir):  # because autodock can't see files in other directories ...

            (rc, stdout, stderr) = ad.prepare_flexreceptor(r=receptor_pdbqt, s=res_string)
            self.logger.debug("RC = {}".format(rc))
            if rc == 0:

                # TODO: autodock should return the names somewhere
                # check the paper
                rigid_receptor = receptor_pdbqt.split('.')[0] + '_rigid.pdbqt'
                flex_receptor = receptor_pdbqt.split('.')[0] + '_flex.pdbqt'

                adContext.receptor.rigid_pdbqt = rigid_receptor
                adContext.receptor.flex_pdbqt = flex_receptor

                adContext.setReceptor(
                    adContext.receptor)  # trick the app into thinking that the receptor changed, in order to update the flexible listview(widget)

                self.logger.info(f'Success generating flexible receptor with flexible residues {res_string}')
            else:
                self.logger.error(stderr)
                self.logger.error(
                    f'Generating receptor {adContext.receptor.name} with flexible residues {res_string} failed!')


# ModelView architecture of PyQt - the only place where it is used is in the results model in the results tab

class ResultsModel(QtCore.QAbstractTableModel):
    """
    Specify how to access and present the data.
    """
    
    header_labels = ['Compound', 'Pose', 'Score']

    def __init__(self, data) -> None:
        super().__init__()
        self._data = data

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return self.header_labels[section]
        return QtCore.QAbstractTableModel.headerData(self, section, orientation, role)

    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole:
            value = self._data[index.row()][index.column()]
            
            if isinstance(value, float):
                return "%.2f" % value
            
            if isinstance(value, str):
                return '"%s"' % value
        
            return value

    def rowCount(self, index):
        return len(self._data)
    
    def columnCount(self, index):
        return len(self._data[0])
    
    def setData(self, data):
        self._data = data


class Vina:

    def __init__(self):
        self.load_commands()
            

    def load_commands(self):
        adContext = ADContext()
        tools = {}
        VINA_MODULE_LOADED = module_loaded('vina')
        VINA_IN_PATH = in_path('vina')

        if not VINA_MODULE_LOADED and not VINA_IN_PATH:
            if adContext.config['vina_path'] is None:
                #full_command = os.path.join(adContext.config['vina_path'], command_name)
                return
                
            else:
                full_command = adContext.config['vina_path']
        else:
            full_command = 'vina'

        tools['vina'] = create_tool('Vina', full_command, None)()
        self.__dict__.update(tools)
        adContext.vina_tools_loaded = True
        return tools


class AutoDock:  # circular imports, ADContext uses AutoDock which uses ADContext
    tool_names = None
    tools_loaded_successfuly = False

    def __init__(self):
        self.AD_MODULE_LOADED = module_loaded('ADFRSuite') or module_loaded('mgltools')
        self.load_command_names()
        self.load_commands()

    def load_command_names(self):
        adContext = ADContext()
        
        if self.AD_MODULE_LOADED:
            self.tool_names = ['prepare_gpf', 'autogrid4', 'prepare_receptor', 'prepare_ligand', 'prepare_flexreceptor.py', 'ls']
        else:
            if adContext.config['ad_tools_path'] is None: # TODO: (review) in case ad_tools_path is an empty string, invidual tools will fail to load, and will be caught upon command execution
                return

            # save the absolute paths
            self.tool_names = [f for f in os.listdir(adContext.config['ad_tools_path']) if os.path.isfile(os.path.join(
            adContext.config['ad_tools_path'], f))]

    def load_commands(self):
        tools = {}
        adContext = ADContext()

        if self.tool_names is None:
            #print('AutoDock Tools could not be found in your system!')
            return

        # Special care taken for autogrid4 executable
        if adContext.config['autogrid_path'] is None:
            print('AUTOGRID path not found!')
        else:
            full_command = adContext.config['autogrid_path']
            tools['autogrid'] = create_tool('Autogrid', full_command, None)()

        for command_name in self.tool_names:
            cls_name = clsname_from_cmdname(command_name)
            if cls_name == 'prepare_gpf':
                    print('PREPARE_GPF LOADED!')

            if self.AD_MODULE_LOADED:
                full_command = command_name
                tools[cls_name.lower()] = create_tool(cls_name, full_command, None)()

            else:
                # full command now contains the absoulte path; and the python executable is needed; if not provided, the CustomCommand
                # will take care of including it, but it's success depends on the current system being used
                full_command = os.path.join(adContext.config['ad_tools_path'], command_name)
                tools[cls_name.lower()] = create_tool(cls_name, full_command, adContext.config['mgl_python_path'])()

        self.__dict__.update(tools)
        adContext.ad_tools_loaded = True
        #self.tools_loaded_successfuly = True
        return tools


class ADContext:
    """
    ADContext knows everything, acting as a registry, bookkeeping every action.

    ADContext doesn't know how you generated receptors, or how you prepared the ligands, another piece of code
    is responsible for that, but however, ADContext is always notified if a receptor was generated or not.
    This poses a new threat; if you decide to run the generation, preparation, etc. steps (in general, any process
    for which ADContext will be notified) in separate threads, synchronization problems may arise. In this approach,
    ADContext is a singleton, and it should be made thread safe so whenever a thread wants to access the vinaInstance,
    it must do so in a "safe" way.
    XXX: So far the application doesn't spawn multiple threads, so it's safe to keep ADContext this way.

    NOTE: The tools to run docking are delegated to their respective classes.

    """

    class __ADContext:

        def __init__(self) -> None:

            self.receptor = None
            self.ligands = {}
            self.ligands_to_dock = {}
            self.receptors = {}
            self.form = None
            self._callbacks = []
            self._ligand_callbacks = []
            self._ligandondock_callbacks = []
            self.ad_tools_loaded = False
            self.vina_tools_loaded = False
            self.affinity_map = None
            self.gpf = None

            # TODO: remove these from config dict
            self.config = { 'vina_path': None, 
                            'ad_tools_path': None, 
                            'mgl_python_path': None, 
                            'last_saved_box_path': None, 
                            'box_path': None, 
                            'output_file': None,
                            'autogrid_path': None,
                            'dockingjob_params': {
                                'exhaustiveness': 8,
                                'n_poses': 9,
                                'min_rmsd': 1,
                                'max_evals': 0,
                                'scoring': 'vina',
                                'energy_range': 3
                            },
                            
                            'ligandjob_params': {
                               'ph': None
                            },
                           
                           #'working_dir': os.getcwd() or None,
                            'working_dir': None }

            self.ligand_to_dock = None
            self.ad_command_list = ['prepare_receptor', 'prepare_ligand', 'prepare_flexreceptor.py', 'ls']
            self.vina_command_list = ['vina']

            self.ad_tools_path = None
            self.vina_tools_path = None

        def getReceptor(self):
            return self.receptor

        def setReceptor(self, receptor):
            self.receptor = receptor
            self._notify_observers()

    
        # Callbacks act as Observers   

        def _notify_observers(self):
            for callback in self._callbacks:
                callback()

        def _notify_ligand_observers(self):
            for callback in self._ligand_callbacks:
                callback()

        def register_callback(self, callback):
            self._callbacks.append(callback)

        def register_ligand_callback(self, callback):
            self._ligand_callbacks.append(callback)

        def add_callback(self, callback, cbtype):
            self.__dict__[cbtype].append(callback)

        def setForm(self, form):
            self.form = form

        def setLigands(self, ligands):
            self.ligands = ligands

        def addLigand(self, ligand):
            self.ligands[ligand.name] = ligand
            self._notify_ligand_observers()

        def removeLigand(self, l_id):
            del self.ligands[l_id]
            # self.ligands.pop(l_id, None)
            # self._notify_ligand_observers()

        def addReceptor(self, receptor):
            self.receptors[receptor.name] = receptor
            receptor.onReceptorAdded()
            self.setReceptor(receptor)

        def signalLigandAction(self):
            self._notify_ligand_observers()

        def signalReceptorAction(self):
            self._notify_observers()

        def removeReceptor(self, r_id):
            self.receptors.pop(r_id, None)

        def get_ad_tools_path(self):
            return self.ad_tools_path

        def set_ad_tools_path(self, value):
            self.ad_tools_path = value

        def get_vina_tools_path(self):
            return self.vina_tools_path

        def set_vina_tools_path(self, value):
            self.vina_tools_path = value

    _instance = None

    def __init__(self):
        if not ADContext._instance:
            ADContext._instance = ADContext.__ADContext()

    # Delegate calls - needed only if you don't use getInstance()
    def __getattr__(self, name):
        return getattr(self._instance, name)


###################################################### GUI #############################################################


dialog = None


def run_plugin_gui():
    """
    Open our custom dialog
    """
    global dialog

    if dialog is None:
        dialog = make_dialog()

    dialog.show()


def make_dialog():
    # entry point to PyMOL's API
    # from pymol import stored

    cmd.set("auto_zoom", "off")

    # pymol.Qt provides the PyQt5 interface, but may support PyQt4
    # and/or PySide as well
    from pymol.Qt import QtWidgets
    from pymol.Qt import QtCore
    
    from pymol.Qt.utils import loadUi
    from pymol.Qt.utils import getSaveFileNameWithExt

    boxAPI = BoxAPI()
    adContext = ADContext()

    # create a new Window
    qDialog = QtWidgets.QDialog()

    # populate the Window from our *.ui file which was created with the Qt Designer
    uifile = os.path.join(os.path.dirname(__file__), 'magidockwidget.ui')
    form = loadUi(uifile, qDialog)

    adContext.setForm(form)

    plugin_directory = os.path.dirname(__file__)

    logger = logging.getLogger(__name__)

    """ Multiple handlers can be created if you want to broadcast to many destinations. """
    log_box_handler = CustomWidgetLoggingHandler(form.plainTextEdit)
    log_box_handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))

    logger.addHandler(log_box_handler)
    logger.setLevel(logging.DEBUG)

    def startup():
        
        if os.path.isfile(os.path.join(plugin_directory, 'config.json')):
            with open(os.path.join(plugin_directory, 'config.json'), 'r') as f:
                config_data = json.load(f)
            
            adContext.config['mgl_python_path'] = config_data['mgl_python_path']
            form.mglbinPath_txt.setText(adContext.config['mgl_python_path'])

            adContext.config['ad_tools_path'] = config_data['ad_tools_path']
            form.adToolsPath_txt.setText(adContext.config['ad_tools_path'])

            adContext.config['vina_path'] = config_data['vina_path']
            form.vinaPath_txt.setText(adContext.config['vina_path'])

            adContext.config['working_dir'] = config_data['working_dir']
            form.workignDir_txt.setText(adContext.config['working_dir'])

            adContext.config['box_path'] = config_data['box_path']
            form.configPath_txt.setText(adContext.config['box_path'])

            adContext.config['autogrid_path'] = config_data['autogrid_path']
            form.autogridPath_txt.setText(adContext.config['autogrid_path'])

        else:
            with open(os.path.join(plugin_directory, 'config.json'), 'w') as f:
                json.dump(adContext.config, f)

        form.exhaust_txt.setText(str(adContext.config['dockingjob_params']['exhaustiveness']))
        form.numPoses_txt.setText(str(adContext.config['dockingjob_params']['n_poses']))
        form.energyRange_txt.setText(str(adContext.config['dockingjob_params']['energy_range']))
        form.minRMSD_txt.setText(str(adContext.config['dockingjob_params']['min_rmsd']))
        form.scoring_comboBox.setCurrentText(adContext.config['dockingjob_params']['scoring'])

        # Initiates the table view model for the results table
        myTableModel = ResultsModel(data=[[]])
        form.results_model = myTableModel
        form.results_table.setModel(form.results_model)

        ad4 = adContext.config['dockingjob_params']['scoring'] == 'ad4'
        vinardo = adContext.config['dockingjob_params']['scoring'] == 'vinardo'

        form.generateAffinityMaps_btn.setEnabled(ad4)
        if ad4 or vinardo:
            form.preparedLigands_lstw_2.clearSelection()
            form.preparedLigands_lstw_2.setSelectionMode(1)
        else:
            form.preparedLigands_lstw_2.setSelectionMode(2)

    def printRecChange():
        print(f'New receptor is{adContext.receptor.name}!')

    def onLoadedReceptorChanged():
        logger.info("Updating flexible list and loadedReceptor ... ")
        form.loadedReceptor_txt.setText(adContext.receptor.name)
        update_flexible_list()

    def onLigandChanged():
        form.ligands_lstw.clear()
        ligand_names = [lig_id for lig_id in adContext.ligands.keys()]
        form.ligands_lstw.addItems(ligand_names)

        logger.info("Updated ligand list widget!")

    def onPreparedLigandChange():
        """ Callback called when a ligand is added or prepared, or when a prepared_ligand is imported. Whenever there
        is an action with a ligand, this function is called, and if it happens that the ligand on which was acted
        is prepared, the corresponding units will respond. """
        form.preparedLigands_lstw.clear()
        form.preparedLigands_lstw_2.clear()
        prepared_ligands_names = [lig_id for lig_id in adContext.ligands.keys() if
                                  adContext.ligands[lig_id].isPrepared()]

        logger.debug(
            "onPreparedLigandChange() talking: List of prepared_ligands as observed by me is {}')"
                .format(prepared_ligands_names)
        )

        logger.info("Updated prepared ligands list widget!")

        form.preparedLigands_lstw.addItems(prepared_ligands_names)
        form.preparedLigands_lstw_2.addItems(prepared_ligands_names)

    def onReceptorAdded():
        update_receptor_list()

    def onLigandToDockChanged():
        pass

    adContext.register_callback(printRecChange)
    adContext.register_callback(onLoadedReceptorChanged)
    adContext.register_ligand_callback(onLigandChanged)
    adContext.register_ligand_callback(onPreparedLigandChange)

    # adContext.add_callback(onLigandToDockAdded, '_ligandondock_callbacks')

    def updateCenterGUI(x, y, z):
        form.centerX.setValue(x)
        form.centerY.setValue(y)
        form.centerZ.setValue(z)

    def updateDimGUI(x, y, z):
        form.dimX.setValue(x)
        form.dimY.setValue(y)
        form.dimZ.setValue(z)

    def updateGUIdata():
        boxData = boxAPI.box_data()
        updateCenterGUI(boxData.center.x, boxData.center.y, boxData.center.z)
        updateDimGUI(boxData.dim.x, boxData.dim.y, boxData.dim.z)

    if boxAPI.box_exists():
        boxConfig = boxAPI.box_data()
        updateCenterGUI(boxConfig.center.x, boxConfig.center.y, boxConfig.center.z)
        updateDimGUI(boxConfig.dim.x, boxConfig.dim.y, boxConfig.dim.z)

    ########################## <Callbacks> #############################

    def update_box():
        adContext = ADContext()
        if boxAPI.box_exists():
            centerX = form.centerX.value()
            centerY = form.centerY.value()
            centerZ = form.centerZ.value()
            dimX = form.dimX.value()
            dimY = form.dimY.value()
            dimZ = form.dimZ.value()

            boxAPI.set_center(centerX, centerY, centerZ)
            boxAPI.set_dim(dimX, dimY, dimZ)

            working_dir = adContext.config['working_dir']
            if working_dir == None:
                print("Please specify the working directory first!")
                logging.info("Please specify the working directory first!")
                return

            box_save_path = os.path.join(working_dir, "current_box.txt")
            try:
                boxAPI.save_box(box_save_path, '')
                adContext.config['box_path'] = box_save_path
                form.configPath_txt.setText(adContext.config['box_path'])
            except Exception as e:
                raise e


    def gen_box():
        selection = form.selection_txt.text().strip() if form.selection_txt.text() != '' else '(sele)'
        boxAPI.gen_box(selection=selection)
        updateGUIdata()

    def get_config():
        # When reading a box, the save button should act upon the path from which the box was loaded
        adContext = ADContext()
        filename = form.config_txt.text()
        if filename == '':
            logger.info("Please specify the path of the box first!")
            return
        boxAPI.read_box(filename)
        updateGUIdata()
        adContext.config['last_saved_box_path'] = filename

    def save_config():
        adContext = ADContext()
        if adContext.config['last_saved_box_path'] is not None:
            boxAPI.save_box(adContext.config['last_saved_box_path'], '')
        else:
            saveAs_config()

    # TODO: add save functionality
    def saveAs_config():
        filename = getSaveFileNameWithExt(
            qDialog, 'Save As...', filter='All Files (*.*)'
        )
        global saveTo
        saveTo = filename 
        boxAPI.save_box(filename, '')
        # When using the Save as button, the save button will act upon that path
        adContext.config['last_saved_box_path'] = filename
        # adContext.config['box_path'] = filename

    def browse():
        # filename = getSaveFileNameWithExt(
        #     dialog, 'Open', filter='All Files (*.*)'
        # )
        filename = QtWidgets.QFileDialog.getOpenFileName(
            qDialog, 'Open', filter='All Files (*.*)'
        )
        if filename != ('', ''):
            form.config_txt.setText(filename[0])

    def browse_ligands():
        filename = QtWidgets.QFileDialog.getOpenFileName(
            qDialog, 'Open', filter='All Files (*.*)'
        )

        if filename != ('', ''):
            form.ligandPath_txt.setText(filename[0])

    def browse_receptors():
        filename = QtWidgets.QFileDialog.getOpenFileName(
            qDialog, 'Open', filter='All Files (*.*)'
        )

        if filename != ('', ''):
            form.receptorPath_txt.setText(filename[0])

    def browse_prepared_ligands():
        filename = QtWidgets.QFileDialog.getOpenFileName(
            qDialog, 'Open', filter='All Files (*.*)'
        )

        if filename != ('', ''):
            form.preparedLigand_txt.setText(filename[0])

    def show_hide_Box():
        if form.showBox_ch.isChecked():
            boxAPI.show_box()
            form.centerX.setDisabled(False)
            form.centerY.setDisabled(False)
            form.centerZ.setDisabled(False)
            form.dimX.setDisabled(False)
            form.dimY.setDisabled(False)
            form.dimZ.setDisabled(False)
        else:
            boxAPI.hide_box()
            form.centerX.setDisabled(True)
            form.centerY.setDisabled(True)
            form.centerZ.setDisabled(True)
            form.dimX.setDisabled(True)
            form.dimY.setDisabled(True)
            form.dimZ.setDisabled(True)

    def fill_unfill_Box():
        if form.fillBox_ch.isChecked():
            boxAPI.fill()
        else:
            boxAPI.unfill()

    def updateStepSize():
        step_size = form.step_size.value()
        form.centerX.setSingleStep(step_size)
        form.centerY.setSingleStep(step_size)
        form.centerZ.setSingleStep(step_size)
        form.dimX.setSingleStep(step_size)
        form.dimY.setSingleStep(step_size)
        form.dimZ.setSingleStep(step_size)

    # TODO: make an observer
    def import_sele():
        # NOTE: using a listwidget for the selections view, because it is a higher level class, inheriting from
        # ListView. Use ListView if you want greater customization.
        selections = cmd.get_names("selections") + cmd.get_names()
        if 'axes' in selections:
            selections.remove('axes')
        if 'box' in selections:
            selections.remove('box')

        form.sele_lstw.clear()
        form.sele_lstw.addItems(selections)

        form.sele_lstw_2.clear()
        form.sele_lstw_2.addItems(selections)

        logger.info('Selections imported!')

    # ligand handler methods

    def OnAddLigandClicked():
        selected_ligands = form.sele_lstw_2.selectedItems()
        ligandController = LigandJobController(form)
        ligandController.add_ligands(selected_ligands)

        form.sele_lstw_2.clearSelection()

    def load_ligand():
        ligand_path = form.ligandPath_txt.text().strip()
        ligandController = LigandJobController(form)
        ligandController.load_ligand(ligand_path)

    def load_prepared_ligand():
        prepared_ligand_path = form.preparedLigand_txt.text().strip()
        ligandController = LigandJobController(form)
        ligandController.load_prepared_ligand(prepared_ligand_path)

    def load_receptor():
        receptor_pdbqt_path = form.receptorPath_txt.text().strip()
        if receptor_pdbqt_path.split('.')[1] != 'pdbqt':
            logger.info('The receptor must be in pdbqt format!')
            return

        receptor_name = receptor_pdbqt_path.split('/')[-1].split('.')[0]

        receptor = Receptor(receptor_name, receptor_pdbqt_path, onReceptorAdded=onReceptorAdded)
        receptor.fromPymol = False
        adContext.addReceptor(receptor)
        cmd.load(receptor_pdbqt_path, object=receptor_name)
        logger.debug("Loaded Receptor = {}".format(adContext.receptor))

    def remove_ligand():
        selection = form.ligands_lstw.selectedItems()
        ligandController = LigandJobController(form)
        ligandController.remove_ligands(selection)

    def update_receptor_list():
        form.receptor_lstw.clear()
        receptor_names = [rec_id for rec_id in adContext.receptors.keys()]
        form.receptor_lstw.addItems(receptor_names)
        # TODO: add tooltips here
        
    # TODO: the same as with OnDockingJobClicked, get the list of Entities here, and pass them to their respective
    #  controllers

    # Controller classes are initialized for each job, thus getting new loggers every instantiation
    # causing the log handlers to be "reloaded" (TODO: should be fixed in the future).
    #  Even though right now the Controllers are used as
    # "static" classes, the functionality may change in the future, so instantiating them for each run
    # is convenient right now. The same controllers used here, may be used for other actions on the entities.

    # NOTE: right here, by making controllers return messages on the task outcome, users can be notified
    # using "windows", "forms", etc.
    # i.e. result = rigidReceptor.run() or result = rigidReceptor.getResultMessage() and showPopUpDialog(result)

    def OnGenerateReceptorClicked():
        rigidReceptorController = RigidReceptorController(form, callbacks={'onReceptorAdded': onReceptorAdded})
        rigidReceptorController.run()

    def OnGenerateFlexibleClicked():
        flexibleReceptorController = FlexibleReceptorController(form)
        flexibleReceptorController.run()

    def OnPrepareLigandsClicked():
        selectedLigands = form.ligands_lstw.selectedItems()
        ligandController = LigandJobController(form)
        ligandController.prepare_ligands(selectedLigands)

    def OnRunDockingJobClicked(multiple_ligands_docking):
        # Notify adContext about the ligands the user wishes to be docked
        selectedLigands = form.preparedLigands_lstw_2.selectedItems()
        adContext.ligands_to_dock.clear()
        for index, sele in enumerate(selectedLigands):
            ligand = adContext.ligands[sele.text()]
            adContext.ligands_to_dock[sele.text()] = ligand

        dockingJobController = DockingJobController(form, multiple_ligands_docking)
        dockingJobController.run()

    def OnRunDockingWrapper(multiple_ligands_docking):
        return lambda: OnRunDockingJobClicked(multiple_ligands_docking)

    def OnGenerateAffinityMapsClicked():
        selectedLigands = form.preparedLigands_lstw_2.selectedItems()
        dockingJobController = DockingJobController(form)
        dockingJobController.generateAffinityMaps(selectedLigands)

    # "button" callbacks
    def onSelectGeneratedReceptor(item):
        logger.info(f'Receptor {item.text()} selected')
        # adContext.receptor = adContext.receptors[item.text()]
        adContext.setReceptor(adContext.receptors[item.text()])
        # adContext.setRecTest(adContext.receptors[item.text()])
        # update_flexible_list() # TODO: refactor, on receptor_change (done)

    def onSelectLigandToDock(item):
        """ Sets ADContext ligand to dock (not useful right now, if multiple ligands supported) """
        adContext.setLigandToDock(adContext.ligands[item.text()])
        logger.info("Ligand to dock is: {} at {}".format(adContext.ligand_to_dock.name, adContext.ligand_to_dock.pdbqt))

    def update_flexible_list():
        form.flexRes_lstw.clear()
        flexibles = adContext.receptor.flexible_residues
        if len(flexibles) != 0:
            for chain, contents in flexibles.items():
                for res in contents:
                    form.flexRes_lstw.addItem(f'{chain} : {str(res.resn)}{str(res.resi)}')

    def fill_test():
        boxAPI.fill()

    def saveConfig():
        adfrPath = form.adfrPath_txt.text()
        mglPath = form.mglPath_txt.text()
        vinaPath = form.vinaPath_txt.text()
        configPath = form.configPath_txt.text()
        adContext.config['adfr'] = adfrPath
        adContext.config['mglPath'] = mglPath
        adContext.config['vinaPath'] = vinaPath
        adContext.config['configPath'] = configPath

    def OnBrowseADFRClicked():
        dir_name = str(QtWidgets.QFileDialog.getExistingDirectory(qDialog, "Select Directory"))
        adContext.config['ad_tools_path'] = dir_name
        logger.info("ad_tools_path = {}".format(dir_name))
        form.adfrPath_txt.setText(dir_name)

    def OnBrowseMGLPythonExeClicked():
        filename = QtWidgets.QFileDialog.getOpenFileName(
            qDialog, 'Open', filter='All Files (*.*)'
        )

        if filename != ('', ''):
            form.mglbinPath_txt.setText(filename[0])
            adContext.config['mgl_python_path'] = filename[0]
            logger.info(adContext.config['mgl_python_path'])
            with open(os.path.join(plugin_directory, 'config.json'), 'w') as f:
                json.dump(adContext.config, f)
            

    def OnBrowseADToolsClicked():
        # dir_name = str(QtWidgets.QFileDialog.getExistingDirectory(qDialog, "Select Directory"))
        # adContext.config['mgl_path'] = dir_name
        # logger.info("mgl_path = {}".format(dir_name))
        # form.mglPath_txt.setText(dir_name)

        dir_name = str(QtWidgets.QFileDialog.getExistingDirectory(qDialog, "Select Directory"))
        adContext.config['ad_tools_path'] = dir_name
        #adContext.set_ad_tools_path(dir_name)
        logger.info("ad_tools_path = {}".format(adContext.config['ad_tools_path']))
        form.adToolsPath_txt.setText(dir_name)
        with open(os.path.join(plugin_directory, 'config.json'), 'w') as f:
            json.dump(adContext.config, f)

    def OnBrowseVinaClicked():
        # dir_name = str(QtWidgets.QFileDialog.getExistingDirectory(qDialog, "Select Directory"))
        # adContext.config['vina_path'] = dir_name
        # #adContext.set_vina_tools_path(dir_name)
        # logger.info("Vina path = {}".format(dir_name))
        # form.vinaPath_txt.setText(dir_name)
        # with open(os.path.join(plugin_directory, 'config.json'), 'w') as f:
        #     json.dump(adContext.config, f)

        filename = QtWidgets.QFileDialog.getOpenFileName(
            qDialog, 'Open', filter='All Files (*.*)'
        )

        if filename != ('', ''):
            form.vinaPath_txt.setText(filename[0])
            adContext.config['vina_path'] = filename[0]
            logger.info("Vina path = {}".format(adContext.config['vina_path']))
            with open(os.path.join(plugin_directory, 'config.json'), 'w') as f:
                json.dump(adContext.config, f)

    def OnBrowseConfigClicked():
        filename = QtWidgets.QFileDialog.getOpenFileName(
            qDialog, 'Open', filter='All Files (*.*)'
        )

        if filename != ('', ''):
            form.configPath_txt.setText(filename[0])
            adContext.config['box_path'] = filename[0]
            logger.info(adContext.config['box_path'])
            with open(os.path.join(plugin_directory, 'config.json'), 'w') as f:
                json.dump(adContext.config, f)

    def OnBrowseWorkingDirClicked():
        dir_name = str(QtWidgets.QFileDialog.getExistingDirectory(qDialog, "Select Directory"))
        adContext.config['working_dir'] = dir_name
        logger.info(f'working_dir = {dir_name}')
        form.workignDir_txt.setText(dir_name)
        with open(os.path.join(plugin_directory, 'config.json'), 'w') as f:
            json.dump(adContext.config, f)

    def OnBrowseAutogridClicked():
        filename = QtWidgets.QFileDialog.getOpenFileName(
            qDialog, 'Open', filter='All Files (*.*)'
        )

        if filename != ('', ''):
            form.autogridPath_txt.setText(filename[0])
            adContext.config['autogrid_path'] = filename[0]
            logger.info(adContext.config['autogrid_path'])
            with open(os.path.join(plugin_directory, 'config.json'), 'w') as f:
                json.dump(adContext.config, f)


    def onPHChange():
        adContext.config['ligandjob_params']['ph'] = float(
            form.exhaust_txt.text().strip()) if is_float(form.exhaust_txt.text().strip()) else 7.4
        logger.debug(f"Exhaust set to: {adContext.config['ligandjob_params']['ph']}")

    def OnExhaustChange():
        adContext.config['dockingjob_params']['exhaustiveness'] = int(
            form.exhaust_txt.text().strip()) if form.exhaust_txt.text().strip().isnumeric() else 8
        logger.debug(f"Exhaust set to: {adContext.config['dockingjob_params']['exhaustiveness']}")

    def OnNumPosesChange():
        adContext.config['dockingjob_params']['n_poses'] = int(
            form.numPoses_txt.text().strip()) if form.numPoses_txt.text().strip().isnumeric() else 9
        logger.debug("Num poses set to {}".format(adContext.config['dockingjob_params']['n_poses']))

    def OnEnergyRangeChange():
        adContext.config['dockingjob_params']['energy_range'] = int(
            form.energyRange_txt.text().strip()
        ) if form.energyRange_txt.text().strip().isnumeric() else 3
        logger.debug("Energy range set to {}".format(adContext.config['dockingjob_params']['energy_range']))

    def OnMinRMSDChange():
        adContext.config['dockingjob_params']['min_rmsd'] = int(
            form.minRMSD_txt.text().strip()
        ) if form.minRMSD_txt.text().strip().isnumeric() else 1
        logger.debug("Minimum RMSD set to {}".format(adContext.config['dockingjob_params']['min_rmsd']))

    def OnScoringChange():
        adContext.config['dockingjob_params']['scoring'] = str(form.scoring_comboBox.currentText())
        logger.debug("Scoring set to {}".format(adContext.config['dockingjob_params']['scoring']))

        ad4 = adContext.config['dockingjob_params']['scoring'] == 'ad4'
        vinardo = adContext.config['dockingjob_params']['scoring'] == 'vinardo'

        if ad4 or vinardo:
            form.preparedLigands_lstw_2.clearSelection()
            form.preparedLigands_lstw_2.setSelectionMode(1)
        else:
            form.preparedLigands_lstw_2.setSelectionMode(2)

        form.generateAffinityMaps_btn.setEnabled(ad4)


    def OnLoadResults():
        adContext = ADContext()
        best_pose_only = form.bestPose_checkBox.isChecked()
        output_file = adContext.config['output_file']
        if output_file != None:
            # get scores, and notify the tableview
            scores = get_scores(output_file, best_pose_only)
            formatted_scores = format_scores(scores)
            
            form.results_model.setData(formatted_scores)
            form.results_model.layoutChanged.emit()

            # load graphically


    def OnExportResults():
        adContext = ADContext()
        output_file = adContext.config['output_file']

        if str(form.csvPath_txt.text()) == '' or output_file == None:
            return

        # Read results (results are not loaded and stored inside the app)
        best_pose_only = form.bestPose_checkBox.isChecked()
        scores = get_scores(output_file, best_pose_only)
        formatted_scores = format_scores(scores)
        export_csv(adContext.config['working_dir'], str(form.csvPath_txt.text()), formatted_scores)


    # NOTE: doesn't change the environment of the application (i.e. executing cd will not change the current
    # directory, since that is controlled by the os module). Use the app shell, just for simple commands,
    # i.e. loading modules, checking the current working directory, etc.
    # The shell is not connected to the application state (TODO: to be considered in the future)
    def OnShellCommandSubmitted():
        import subprocess, traceback
        cmd = form.shellInput_txt.text()  # TODO: maybe a better way is to pass it as an argument
        # args = cmd.split(' ')
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

        try:
            out, err = p.communicate()
            rc = p.returncode

            if rc == 0:
                logger.info("Success!")
                logger.info(out.decode('utf-8'))
            else:
                logger.error(f"An error occurred executing: {cmd}")

        except Exception as e:
            logger.error(traceback.format_exc())

        form.shellInput_txt.clear()

    def onCloseWindow():
        cmd.delete('box')
        cmd.delete('axes')
        qDialog.close()

    def dummy():
        logger.debug('Callback works!')

    ########################## </Callbacks> #############################

    # bind callbacks
    form.centerX.valueChanged.connect(update_box)
    form.centerY.valueChanged.connect(update_box)
    form.centerZ.valueChanged.connect(update_box)
    form.dimX.valueChanged.connect(update_box)
    form.dimY.valueChanged.connect(update_box)
    form.dimZ.valueChanged.connect(update_box)
    form.step_size.valueChanged.connect(updateStepSize)
    form.getConfig_btn.clicked.connect(get_config)
    form.save_btn.clicked.connect(save_config)
    form.saveAs_btn.clicked.connect(saveAs_config)
    form.browse_btn.clicked.connect(browse)
    form.browseLigand_btn.clicked.connect(browse_ligands)
    form.browseReceptor_btn.clicked.connect(browse_receptors)
    form.browsePreparedLigand_btn.clicked.connect(browse_prepared_ligands)
    form.genBox_btn.clicked.connect(gen_box)
    form.receptor_lstw.itemClicked.connect(onSelectGeneratedReceptor)
    # form.preparedLigands_lstw_2.itemClicked.connect(onSelectLigandToDock)
    # form.addLigandToDock_btn.clicked.connect(onAddLigandToDock)
    # form.removeLigandToDock_btn.clicked.connect(onRemoveLigandToDock)

    form.genReceptor_btn.clicked.connect(OnGenerateReceptorClicked)
    form.genFlexible_btn.clicked.connect(OnGenerateFlexibleClicked)
    form.genLigands_btn.clicked.connect(OnPrepareLigandsClicked)

    # form.sele_lstw_2.itemClicked(add_ligand)
    form.loadPreparedLigand_btn.clicked.connect(load_prepared_ligand)
    form.removeLigand_btn.clicked.connect(remove_ligand)
    form.addLigand_btn.clicked.connect(OnAddLigandClicked)
    form.loadLigand_btn.clicked.connect(load_ligand)
    form.loadReceptor_btn.clicked.connect(load_receptor)
    form.runDocking_btn.clicked.connect(OnRunDockingWrapper(False))
    form.runMultipleDocking_btn.clicked.connect(OnRunDockingWrapper(True))
    form.generateAffinityMaps_btn.clicked.connect(OnGenerateAffinityMapsClicked)

    form.showBox_ch.stateChanged.connect(show_hide_Box)
    form.fillBox_ch.stateChanged.connect(fill_unfill_Box)

    form.importSele_btn.clicked.connect(import_sele)
    form.close_btn.clicked.connect(onCloseWindow)

    form.exhaust_txt.textChanged.connect(OnExhaustChange)
    form.numPoses_txt.textChanged.connect(OnNumPosesChange)
    form.energyRange_txt.textChanged.connect(OnEnergyRangeChange)
    form.minRMSD_txt.textChanged.connect(OnMinRMSDChange)
    form.scoring_comboBox.currentTextChanged.connect(OnScoringChange)

    # form.browseADFR_btn.clicked.connect(OnBrowseADFRClicked)
    # form.browseMGL_btn.clicked.connect(OnBrowseMGLClicked)
    form.browseMGLbin_btn.clicked.connect(OnBrowseMGLPythonExeClicked)
    form.browseADTools_btn.clicked.connect(OnBrowseADToolsClicked)
    form.browseVina_btn.clicked.connect(OnBrowseVinaClicked)
    form.browseConfig_btn.clicked.connect(OnBrowseConfigClicked)
    form.browseWorkDir_btn.clicked.connect(OnBrowseWorkingDirClicked)
    form.browseAutogrid_btn.clicked.connect(OnBrowseAutogridClicked)
    # form.saveConfig_btn.clicked.connect(saveConfig)

    form.shellInput_txt.returnPressed.connect(OnShellCommandSubmitted)
    form.loadResults_btn.clicked.connect(OnLoadResults)

    form.exportCSV_btn.clicked.connect(OnExportResults)

    startup()

    return qDialog
