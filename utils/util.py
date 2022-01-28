class dotdict(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def touch(filename):
    with open(filename, 'a'):
        pass

def getStatusOutput(command):
    from subprocess import Popen, PIPE, STDOUT
    import os
    import sys
    env = dict(os.environ)
    args = command.split()
    if args[0].endswith('.py'):
        args.insert(0, sys.executable)
    p = Popen(args, stdout=PIPE, stderr=STDOUT, stdin=PIPE, env=env)
    print(args)
    output = p.communicate()[0]
    return p.returncode, output