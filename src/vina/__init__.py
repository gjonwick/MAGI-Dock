"""
Python binding with vina. The most used commands will be included.
TODO: get all vina commands and create a binding for each of them

Example:
    from src.vina import Vina
    vina = Vina()

    # to run docking job
    vina.dock(exhaustiveness=32, n_poses=20)
"""
from src.CommandWrapper import create_tool


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
            tools[command_name] = create_tool(command_name.upper(), command_name, self.sf_name)()

        return tools

vina = Vina()
vina.dock()