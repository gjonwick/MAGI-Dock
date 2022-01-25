import subprocess


# TODO: decide between using subprocess.Popen vs subprocess.run


# class CustomCommand(object):
#     command_name = None
#
#     def __init__(self):
#         pass
#
#     def __call__(self, *args, **kwargs):
#         self._execute(*args, **kwargs)
#
#     def _execute(self, *args, **kwargs):
#         results, p = self._run_command(*args, **kwargs)
#         return results
#
#     def _run_command(self, *args, **kwargs):
#         cmd = self._build_command(*args, **kwargs)
#         p = self._build_process(cmd)
#         out, err = p.communicate()
#         rc = p.returncode
#
#         return (rc, out, err), p
#
#     def _build_command(self, *args, **kwargs):
#         return [self.command_name] + self._formatted_arguments(*args, **kwargs)
#
#     def _formatted_arguments(self, *args, **kwargs):
#         """ Format positional and named arguments in a format acceptable by subprocess.Popen. """
#
#         options = []
#
#         for option, value in kwargs.items():
#             if option.startswith('-' or '--'):
#                 raise Exception('Do not put dashes before named arguments!')
#
#             if len(option) == 1:
#                 option = f'-{option}'  # it was supposed to be a positional ...
#             else:
#                 option = f'--{option}'  # it is a named one
#
#             if value is True:
#                 options.append(option)  # it's a binary
#                 continue
#             elif value is False:
#                 raise ValueError('Do not put False as a value!')
#
#             # format the args
#             if option[:2] == '--':  # always len > 1
#                 options.append(f'{option}={str(value)}')
#             else:  # always len == 1
#                 options.append((option, str(value)))
#
#         return options + list(args)
#
#     def _build_process(self, cmd):
#         try:
#             p = subprocess.Popen(cmd)
#         except:
#             print(f'Error setting up the command')
#             raise
#
#         return p
#

class CustomCommand(object):
    command_name = None

    '''
    Receives init-time args
    '''

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def execute(self, *args, **kwargs):
        print(f'EXECUTE: *args = [{args}], **kwargs = [{kwargs}]')
        print(f'INIT: *args = [{self.args}], **kwargs = [{self.kwargs}]')

        _args, _kwargs = self._combine_arglist(args, kwargs)
        print(f'Combined _args = [{_args}]')
        print(f'Combined _kwargs = [{_kwargs}]')

        results, p = self._run_command(*_args, **_kwargs)
        return results

    '''

    '''

    def _combine_arglist(self, args, kwargs):
        print(f'Combining arguments ... [{self.args}] and [{kwargs}]')
        _args = self.args + args
        _kwargs = self.kwargs | kwargs
        _kwargs.update(kwargs)

        return _args, _kwargs

    def _run_command(self, *args, **kwargs):
        print(f'Just before running Popen ... ')

        p = self.runPopen(*args, **kwargs)
        out, err = p.communicate()
        rc = p.returncode

        return (rc, out, err), p

    '''
    Unifies the command_name and the arguments as a command line
    '''

    def _commandline(self, *args, **kwargs):
        if self.driver is not None:
            return [self.driver, self.command_name] + self.prepare_args(*args, **kwargs)
        return [self.command_name] + self.prepare_args(*args, **kwargs)

    def prepare_args(self, *args, **kwargs):
        ''' Modify arguments in a format acceptable by Popen '''
        options = []

        print(f'Preparing arguments ... ')
        # pre-process 'dict' arguments
        for option, value in kwargs.items():
            print(f'current option = {option}, value = {value}')

            if not option.startswith('-'):

                if len(option) == 1:
                    option = f'-{option}'
                else:
                    option = f'--{option}'

            if value is True:
                options.append(option)
                continue
            elif value is False:
                raise ValueError('False value detected!')

            if option[:2] == '--':
                options.append(f'{option}={str(value)}')  # GNU style
            else:
                options.extend((option, str(value)))  # POSIX style

        return options + list(args)  # append the positional arguments

    def runPopen(self, *args, **kwargs):

        cmd = self._commandline(*args, **kwargs)

        try:
            p = PopenWithInput(cmd)

        except:
            print(f'Error setting up the command')
            raise

        return p

    '''
    Receives execution-time args
    '''

    def __call__(self, *args, **kwargs):
        return self.execute(*args, **kwargs)


class PopenWithInput(subprocess.Popen):

    def __init__(self, *args, **kwargs):
        self.command = args[0]

        super(PopenWithInput, self).__init__(*args, **kwargs)


def create_tool(tool_name, command_name, driver=None):
    tool_dict = {
        'command_name': command_name,
        'driver': driver
    }
    tool = type(tool_name, (CustomCommand,), tool_dict)
    return tool


class Vina:

    command_list = ['set_receptor', 'set_ligand_from_file', 'set_ligand_from_string', 'set_weights', 'compute_vina_maps',
                    'load_maps', 'write_maps', 'write_pose', 'write_poses', 'poses', 'energies', 'randomize', 'score',
                    'optimize', 'dock']

    def __init__(self, sf_name='vina', cpu=0, seed=0, no_refine=False, verbosity=1):
        self.sf_name = sf_name
        self.cpu = cpu
        self.seed = seed
        self.no_refine = no_refine
        self.verbosity = verbosity
        self.__dict__.update(self.load_vina_commands())

    def __str__(self):
        pass

    def load_vina_commands(self):
        tools = {}
        for command_name in self.command_list:
            tools[command_name] = create_tool(command_name.upper(), command_name, 'vina')()

        return tools

vina = Vina()
vina.dock()