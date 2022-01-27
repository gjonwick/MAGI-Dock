"""
    attributes:
        name - acts as an ID
        pdb - the path to the pdb (or .gro, .mol2, etc.) file, if any
        pdbqt - the path to the generated pdbqt file, if any
        fromPymol - flag that tracks if the ligand is loaded from the user's local system, or from pymol
        isPrepared - flag that tracks if the ligand is prepared or not (if prepared, it's ready to use in docking)
"""


class Ligand:

    def __init__(self, name, pdb, onPrepared=None) -> None:
        self.name = name
        self.pdb = pdb
        self.pdbqt = ''
        self.fromPymol = True
        self.prepared = False
        self.onPrepared = onPrepared

    # @property
    def isPrepared(self):
        return self.prepared

    def prepare(self):
        self.prepared = True
        self.onPrepared()

    def __repr__(self):
        pdbqt = 'No PDBQT' if self.pdbqt == '' else self.pdbqt
        isPrepared = 'Prepared' if self.prepared == True else 'Not Prepared'
        return f'Ligand(name={self.name}, pdb={self.pdb}, pdbqt={pdbqt}, status={isPrepared})'

