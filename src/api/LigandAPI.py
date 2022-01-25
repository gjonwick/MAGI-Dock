from src.ADContext import ADContext
from pymol import cmd
import os
import logging
from src.Entities.Ligand import Ligand
from src.utils.util import *


class LigandJobController:

    def __init__(self, form):
        self.form = form

    def run(self):
        pass

    def add(self):
        pass

    '''
       Generates pdbqt files for the ligands

       1. save the molecule as pdb
       2. run prepare ligand to generate pdbqt
    '''

    # "button" callbacks TODO: use the ligand fromPymol flag to distinguish which ligand to choose (the one from the
    #  file, or the one from pymol)
    def prepare(self):
        adContext = ADContext()
        form = self.form

        SUCCESS_FLAG = True
        suffix = ''
        ligand_selection = form.ligands_lstw.selectedItems()

        WORK_DIR = os.getcwd()  # TODO: temporary

        prep_command = 'prepare_ligand'
        if form.checkBox_hydrogens.isChecked():
            suffix = '-A checkhydrogens'

        for index, ligand_selection in enumerate(ligand_selection):
            ligand_name = ligand_selection.text()
            ligand = adContext.ligands[ligand_name]
            if ligand.fromPymol:
                ligand_pdb = os.path.join(WORK_DIR, f'TESTING_LIGAND_{ligand_name}.pdb')
                ligand.pdb = ligand_pdb
                try:
                    cmd.save(ligand_pdb, ligand_name)
                except cmd.QuietException:
                    pass
            else:
                ligand_pdb = ligand.pdb

            ligand_pdbqt = os.path.join(WORK_DIR, f'TESTING_LIGAND_{ligand_name}.pdbqt')
            ligand.pdbqt = ligand_pdbqt

            command = f'{prep_command} -l {ligand_pdb} -o {ligand_pdbqt} {suffix}'

            # result, output = getStatusOutput(command)
            result = 0

            if result == 0:
                # logging.debug(output)
                ligand.prepare()
                # ligand.pdbqt = ligand_pdbqt

                # TODO: prepared ligand was added here to the view, but fix that
                '''
                form.preparedLigands_lstw.addItem(ligand.name)
                form.preparedLigands_lstw_2.addItem(ligand.name)
                '''

                logging.info(f'Ligand {ligand.name} pdbqt generated at {ligand.pdbqt}')
            else:
                logging.info(f'An error occurred while trying to prepare the ligand ...')
                # logging.info(output)
