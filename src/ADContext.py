# TODO: make it thread safe!
from src.CommandWrapper import *
from src.utils.util import *

"""
ADContext knows everything!!!
Think of it as a type of registry (hence, the singleton).

ADContext doesn't know how you generated receptors, or how you prepared the ligands, another piece of code
is responsible for that, but however, ADContext is always notified if a receptor was generated or not.
This poses a new threat; if you decide to run the generation, preparation, etc. steps (in general, any process
for which ADContext will be notified) in separate threads, synchronization problems may arise. In this approach,
ADContext is a singleton, and it should be made thread safe so whenever a thread wants to access the vinaInstance,
it must do so in a "safe" way.

If you generated a receptor, ADContext will know it!
If you prepared a ligand, ADContext will know it!

    attributes: receptor/receptors - an instance holding the receptor/receptors currently initiated by the user 
    ligands - the ligands we wish to bind (they do not belong to receptors, because users will load and execute both 
    receptors and ligands as they wish) XXX:form - XXX:not needed """


class ADContext:
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
            self.config = {'vina_path': None, 'adfr_path': None, 'mgl_path': None, 'box_path': None,
                           'dockingjob_params': {
                               'exhaustiveness': 32,
                               'n_poses': 9,
                               'min_rmsd': 1.0,
                               'max_evals': 0},
                           'working_dir': os.getcwd()}
            self.ligand_to_dock = None
            self.ad_command_list = ['prepare_receptor', 'prepare_ligand', 'prepare_flexreceptor.py', 'ls']
            self.vina_command_list = ['vina']

        """ Maybe get rid of ad and vina classes, and init everything here? Either way, you can just export this code
            to a separate class. """
        # TODO: just return True or False
        def load_ad_tools(self):
            tools = {}
            AD_MODULE_LOADED = module_loaded('ADFRsuite') and module_loaded('mgltools')

            if not AD_MODULE_LOADED:
                if self.config['mgl_path'] is None:
                    print('ADContext here: mgl_path not specified, returning')
                    return None

            for command_name in self.ad_command_list:
                cls_name = clsname_from_cmdname(command_name)
                executable = None
                if not AD_MODULE_LOADED:
                    if command_name[-3:] == '.py':
                        full_command = os.path.join(self.config['mgl_path'], 'MGLToolsPckgs/AutoDockTools/Utilities24',
                                                    command_name)

                    else:
                        full_command = os.path.join(self.config['mgl_path'], 'MGLToolsPckgs/AutoDockTools/Utilities24',
                                                    command_name + '.py')
                    executable = sys.executable
                else:
                    full_command = command_name

                tools[cls_name.lower()] = create_tool(cls_name, full_command, executable)()

            self.__dict__.update(tools)
            self.ad_tools_loaded = True
            return tools

        def load_vina_tools(self):
            tools = {}
            VINA_MODULE_LOADED = module_loaded('vina')

            if not VINA_MODULE_LOADED:
                if self.config['vina_path'] is None:
                    print('ADContext here: vina_path not specified, returning')
                    return None
            
            for command_name in self.vina_command_list:
                cls_name = clsname_from_cmdname(command_name)
                if not VINA_MODULE_LOADED:
                    full_command = os.path.join(self.config['vina_path'], command_name)
                else:
                    full_command = command_name
                
                tools[cls_name.lower()] = create_tool(cls_name, full_command, None)

            self.__dict__.update(tools)
            self.vina_tools_loaded = True
            return tools

        def getReceptor(self):
            return self.receptor    
            
        def setReceptor(self, receptor):
            self.receptor = receptor
            self._notify_observers()

        """
        Callbacks act as Observers, because we will probably not use observer objects, but just methods,
        hence callbacks
        """

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
            self.ligands.pop(l_id, None)
            self._notify_ligand_observers()

        def addReceptor(self, receptor):
            self.receptors[receptor.name] = receptor
            receptor.onReceptorAdded()
            self.setReceptor(receptor)

        def removeReceptor(self, r_id):
            self.receptors.pop(r_id, None)

    _instance = None

    def __init__(self):
        if not ADContext._instance:
            ADContext._instance = ADContext.__ADContext()

    # Delegate calls - needed only if you don't use getInstance()
    def __getattr__(self, name):
        return getattr(self._instance, name)
