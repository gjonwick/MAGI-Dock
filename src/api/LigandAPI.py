from src.ADContext import ADContext
from pymol import cmd
import os
import logging
from src.Entities.Ligand import Ligand
from src.api.BaseController import BaseController
from src.utils.util import *
from src.log.Logger import LoggerFactory
from src.decorators import *

""" LigandJobController may be responsible for different ligand actions (add, loading, and preparing). """


# TODO: CRUD code may be wrapped into a "DAO" object
class LigandJobController(BaseController):

    def __init__(self, form=None, callbacks=None):
        super(LigandJobController, self).__init__(form, callbacks)

    def run(self):
        self.logger.info('Im running fine!')
        self.prepare()

    def _get_logger(self):
        return self.loggerFactory.giff_me_logger(name=__name__, level=logging.DEBUG, destination=self.form.ligandLogBox)

    """ Load an imported ligand to the list of ligands (not prepared). """

    def load_ligand(self, ligand_path):
        adContext = ADContext()

        if ligand_path.split('.') == 'pdbqt':
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
        adContext = ADContext()
        prepared_ligand_name = prepared_ligand_path.split('/')[-1].split('.')[0]
        extension = prepared_ligand_path.split('.')[1]
        if extension != 'pdbqt':
            self.logger.error("Please select a .pdbqt file!")
            return

        ligand = Ligand(prepared_ligand_name, '')
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
        adContext = ADContext()
        for index, sele in enumerate(ligand_widget_list):
            ligand = Ligand(sele.text(), '')  # onPrepared=onPreparedLigandChange
            adContext.addLigand(ligand)

        self.logger.debug("Ligands added = {}".format(adContext.ligands))

    def remove_ligands(self, ligand_widget_list):
        adContext = ADContext()
        for index, item in enumerate(ligand_widget_list):
            adContext.removeLigand(item.text())
            # TODO: remove foreign ligand from pymol (optional)

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
        ligand_selection = form.ligands_lstw.selectedItems()

        SUCCESS_FLAG = True
        suffix = ''

        if not adContext.ad_tools_loaded:
            tools = adContext.load_ad_tools()
            if tools is None:
                self.logger.error(
                    'Could not load AutoDock tools! Please specify the paths, or load the respective modules!')
                return

        working_dir = adContext.config['working_dir']
        with while_in_dir(working_dir):
            arg_dict = {}
            if form.checkBox_hydrogens.isChecked():
                arg_dict.update(A='checkhydrogens')

            for index, ligand_selection in enumerate(ligand_selection):
                ligand_name = ligand_selection.text()
                ligand = adContext.ligands[ligand_name]
                self.logger.debug(f'Currently at ligand from ligand_lstw {ligand_name}')
                if ligand.fromPymol:
                    ligand_pdb = os.path.join(working_dir, f'ad_binding_test_ligand{ligand_name}.pdb')
                    self.logger.debug(f'Generating pdb {ligand_pdb} for ligand {ligand.name}')
                    ligand.pdb = ligand_pdb
                    try:
                        cmd.save(ligand_pdb, ligand_name)
                    except cmd.QuietException:
                        pass
                else:
                    ligand_pdb = ligand.pdb

                ligand_pdbqt = os.path.join(working_dir, "ad_binding_test_ligand{}.pdbqt".format(ligand_name))
                ligand.pdbqt = ligand_pdbqt

                arg_dict.update(l=ligand_pdb, o=ligand_pdbqt)
                (rc, stdout, stderr) = adContext.prepare_ligand(**arg_dict)

                # if stdout is not None:
                #     self.logger.debug(f"{stdout.decode('utf-8')}")

                if rc == 0:
                    ligand.prepare()
                    adContext.signalLigandAction() # TODO: can be fixed by returning a "signal" and the main class
                    # will fire the callbacks
                    self.logger.info(f'Ligand {ligand.name} pdbqt generated at {ligand.pdbqt}')
                else:
                    self.logger.info(f'An error occurred while trying to prepare the ligand ...')
                    #self.logger.error(stderr.decode('utf-8'))
