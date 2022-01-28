from src.ADContext import ADContext
from pymol import cmd
import os
import logging
from src.Entities.Ligand import Ligand
from src.utils.util import *
from src.log.Logger import LoggerFactory
from src.decorators import *


class LigandJobController:

    def __init__(self, form):
        self.form = form
        self.logger = self._get_logger()

    def run(self):
        pass

    def _get_logger(self):
        logger_factory = LoggerFactory()
        return logger_factory.giff_me_logger(name=__name__, level=logging.DEBUG, destination=self.form.ligandLogBox)

    def load_ligand(self):
        adContext = ADContext()
        ligand_pdb_path = self.form.ligandPath_txt.text().strip()

        if ligand_pdb_path.split('.') == 'pdbqt':
            self.logger.error(f'PDBQTs not accepted here!')
            # return

        ligand_name = ligand_pdb_path.split('/')[-1].split('.')[0]

        ligand = Ligand(ligand_name, ligand_pdb_path)  # onPrepared=onPreparedLigandChange
        ligand.fromPymol = False
        adContext.addLigand(ligand)
        cmd.load(ligand_pdb_path, object=ligand_name)

    def add(self):
        adContext = ADContext()
        selected_ligands = self.form.sele_lstw_2.selectedItems()
        self.logger.debug(f'Ligands to be added are: {selected_ligands}')
        for index, sele in enumerate(selected_ligands):
            ligand = Ligand(sele.text(), '')  # onPrepared=onPreparedLigandChange
            adContext.addLigand(ligand)

        self.logger.debug(adContext.ligands)
        self.form.sele_lstw_2.clearSelection()

    '''
       Generates pdbqt files for the ligands

       1. save the molecule as pdb
       2. run prepare ligand to generate pdbqt
    '''

    # "button" callbacks TODO: use the ligand fromPymol flag to distinguish which ligand to choose (the one from the
    #  file, or the one from pymol)
    # @info_logger
    def prepare(self):
        # TODO: when ligand is already prepared, what to do?
        adContext = ADContext()
        form = self.form
        WORK_DIR = ADContext.config.pop('working_dir', False)
        if not WORK_DIR:
            WORK_DIR = os.getcwd()

        SUCCESS_FLAG = True
        suffix = ''
        ligand_selection = form.ligands_lstw.selectedItems()

        prep_command = 'prepare_ligand'
        if form.checkBox_hydrogens.isChecked():
            suffix = '-A checkhydrogens'

        for index, ligand_selection in enumerate(ligand_selection):
            ligand_name = ligand_selection.text()
            ligand = adContext.ligands[ligand_name]
            self.logger.debug(f'Currently at ligand from ligand_lstw {ligand_name}')
            if ligand.fromPymol:
                ligand_pdb = os.path.join(WORK_DIR, f'TESTING_LIGAND_{ligand_name}.pdb')
                self.logger.debug(f'Generating pdb {ligand_pdb} for ligand {ligand.name}')
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
            # TODO: should look something like: command = ad.prepare_ligand(l=ligand_pdb, o=ligand_pdbqt)
            # result should be handled by the command wrapper, not here

            # result, output = getStatusOutput(command)
            result = 0

            if result == 0:
                # self.logger.debug(output)
                ligand.prepare()
                # ligand.pdbqt = ligand_pdbqt

                # TODO: prepared ligand was added here to the view, but fix that
                '''
                form.preparedLigands_lstw.addItem(ligand.name)
                form.preparedLigands_lstw_2.addItem(ligand.name)
                '''

                self.logger.info(f'Ligand {ligand.name} pdbqt generated at {ligand.pdbqt}')
            else:
                self.logger.info(f'An error occurred while trying to prepare the ligand ...')
                # self.logger.info(output)
