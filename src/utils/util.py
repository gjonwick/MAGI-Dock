import errno
from contextlib import contextmanager
import os


def touch(filename):
    with open(filename, 'a'):
        pass


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


def execute_command(command):
    import subprocess, os, sys

    env = dict(os.environ)
    args = command.split()
    if args[0].endswith('.py'):
        args.insert(0, sys.executable)
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE, env=env)
    print(args)
    output = p.communicate()[0]
    return p.returncode, output


def getStatusOutput(command):
    MODULE_UNLOADED = False
    from subprocess import Popen, PIPE, STDOUT
    import os, sys
    env = dict(os.environ)
    args = command.split()
    if args[0].endswith('.py') and MODULE_UNLOADED:
        args.insert(0, sys.executable)
    p = Popen(args, stdout=PIPE, stderr=STDOUT, stdin=PIPE, env=env)
    print(args)
    output = p.communicate()[0]
    return p.returncode, output

""" Helper code to deal with environment modules. """

def loaded_modules():
    return os.environ['LOADEDMODULES'].split(':')

def module_loaded(module_name):
    """ Checks if a module (as in CentOS modules) is loaded. """
    # lsmod_proc = subprocess.Popen(['module list'], stdout=subprocess.PIPE)
    # gerp_proc = subprocess.Popen(['grep', module], stdin=lsmod_proc.stdout)
    # grep_proc.communicate()
    # return grep_proc.returncode == 0

    lmods = loaded_modules()
    flag = False
    for module in lmods:
        if module_name.lower() in module.lower():
            flag = True
            break

    return flag

def find_executables(path):
    execs = []
    for exe in os.listdir(path):
        full_exe_path = os.path.join(path, exe)
        if (os.access(full_exe_path, os.X_OK)) and not os.path.isdir(fullexe):
            execs.append(exe)
        
    return execs


class dotdict(dict):
    """ Convenient class to represent dictionaries in a dotted format """
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
