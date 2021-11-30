# TODO: make it thread safe!

"""
ADContext knows everything!!!
Think of it as a type of registry (hence, the singleton).

ADContext doesn't know how you generated receptors, or how you prepared the ligands, another piece of code
is responsible for that, but however, ADContext is always notified if a receptor was generated or not.
This poses a new threat; if you decide to run the generation, preparation, etc. steps (in general, any process
for which ADContext will be notified) in seperate threads, synchronyzation problems may arise. In this approach,
ADContext is a singleton, and it should be made thread safe so whenever a thread wants to access the vinaInstance,
it must do so in a "safe" way.

If you generated a receptor, ADContext will know it!
If you prepared a ligand, ADContext will know it!

    attributes:
        receptor/receptors - an instance holding the receptor/receptors currently initiated by the user
        ligands - the ligands we wish to bind (they do not belong to receptors, because users will load and execute both receptors and ligands as they wish)
    XXX:form - XXX:not needed
"""


# TODO: observer pattern to notify observers when receptor changes (done)

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
            self.config = {}
            self.ligand_to_dock = None

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

        def setFlexibleResidues(self, residues):
            self.flexibleResidues = residues

        def setLigands(self, ligands):
            self.ligands = ligands

        def addLigand(self, ligand):
            self.ligands[ligand.name] = ligand
            self._notify_ligand_observers()

        def removeLigand(self, id):
            self.ligands.pop(id, None)
            self._notify_ligand_observers()

        def addReceptor(self, receptor):
            self.receptors[receptor.name] = receptor
            receptor.onReceptorAdded()
            self.setReceptor(receptor)

        def removeReceptor(self, id):
            self.receptors.pop(id, None)

    _instance = None

    def __init__(self):
        if not ADContext._instance:
            ADContext._instance = ADContext.__ADContext()

    # Delegate calls - needed only if you don't use getInstance()
    def __getattr__(self, name):
        return getattr(self._instance, name)
