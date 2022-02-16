import random
import time
import uuid

from src.ADContext import ADContext
from pymol import cmd
from pymol.Qt import QtCore

from src.Entities.Ligand import Ligand
from src.api.BaseController import BaseController
from src.utils.util import *
from src.decorators import *
from src.log.LoggingModule import LoggerAdapter, SignalAdapter

""" LigandJobController may be responsible for different ligand actions (add, loading, and preparing). """


# TODO: CRUD code may be wrapped into a "DAO" object
class LigandJobController(BaseController):

    def __init__(self, form=None, callbacks=None):
        super(LigandJobController, self).__init__(form, callbacks)
        self.threadpool = QtCore.QThreadPool()
        self.adContext = ADContext()

    def run(self):
        self.logger.info('Im running fine!')
        self.prepare()

    def _get_logger(self):
        return self.loggerFactory.giff_me_logger(name=__name__, level=logging.DEBUG, destination=self.form.ligandLogBox)

    """ Load an imported ligand to the list of ligands (not prepared). """

    def load_ligand(self, ligand_path):
        adContext = self.adContext

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
        adContext = self.adContext
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
        adContext = self.adContext
        for index, sele in enumerate(ligand_widget_list):
            ligand = Ligand(sele.text(), '')  # onPrepared=onPreparedLigandChange
            adContext.addLigand(ligand)

        self.logger.debug("Ligands added = {}".format(adContext.ligands))

    def remove_ligands(self, ligand_widget_list):
        adContext = self.adContext
        for index, item in enumerate(ligand_widget_list):
            adContext.removeLigand(item.text())
            # TODO: remove foreign ligand from pymol (optional)
        adContext.signalLigandAction()

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
        adContext = self.adContext
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
                adContext.prepare_ligand.attach_logging_module(LoggerAdapter(self.logger))
                (rc, stdout, stderr) = adContext.prepare_ligand(**arg_dict)

                # if stdout is not None:
                #     self.logger.debug(f"{stdout.decode('utf-8')}")

                if rc == 0:
                    ligand.prepare()
                    adContext.signalLigandAction()  # TODO: can be fixed by returning a "signal" and the main class
                    # will fire the callbacks
                    self.logger.info(f'Ligand {ligand.name} pdbqt generated at {ligand.pdbqt}')
                else:
                    self.logger.info(f'An error occurred while trying to prepare the ligand ...')
                    # self.logger.error(stderr.decode('utf-8'))

    def prepare_ligands(self, ligand_widget_list):
        adContext = self.adContext
        if len(ligand_widget_list) == 0:
            self.logger.info(
                'Select a ligand please!'
            )
            return

        if not adContext.ad_tools_loaded:
            tools = adContext.load_ad_tools()
            if tools is None:
                self.logger.error(
                    'Could not load AutoDock tools! Please specify the paths, or load the respective modules!')
                return

        worker = PreparationWorker(self.form, ligand_widget_list)
        worker.signals.progress.connect(lambda x: self.logger.info(x))
        worker.signals.finished.connect(self.onFinished)
        worker.signals.success.connect(self.onSuccess)
        worker.signals.error.connect(self.onError)
        worker.signals.pdb_update.connect(self.onPDBUpdate)

        self.form.genLigands_btn.setEnabled(False)
        self.form.loadLigand_btn.setEnabled(False)
        self.form.removeLigand_btn.setEnabled(False)
        self.form.addLigand_btn.setEnabled(False)
        self.threadpool.start(worker)

    def onFinished(self, msg):
        self.form.genLigands_btn.setEnabled(True)
        self.form.loadLigand_btn.setEnabled(True)
        self.form.removeLigand_btn.setEnabled(True)
        self.form.addLigand_btn.setEnabled(True)
        self.logger.info(msg + " ===== Finished! ===== ")
        self.adContext.signalLigandAction()

    def onSuccess(self, ligand):
        ligand.prepare()
        #self.adContext.signalLigandAction()
        self.logger.info("Ligand {} pdbqt generated at {}".format(ligand.name, ligand.pdbqt))

    def onError(self, msg):
        self.logger.error(msg)

    def onPDBUpdate(self, ligand):
        try:
            cmd.save(ligand.pdb, ligand.name)
        except cmd.QuietException:
            pass


class WorkerSignals(QtCore.QObject):
    """ Class containing the signals, since we must inherit from QObject. """

    progress = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal(str)
    success = QtCore.pyqtSignal(Ligand)
    error = QtCore.pyqtSignal(str)
    progress_bar = QtCore.pyqtSignal(float)
    pdb_update = QtCore.pyqtSignal(Ligand)


class PreparationWorker(QtCore.QRunnable):
    """ Thread that deals with the actual process of ligand preparation. """

    def __init__(self, form, ligands):
        super(PreparationWorker, self).__init__()
        self.form = form
        self.ligands = ligands
        self.signals = WorkerSignals()
        self.adContext = ADContext()
        self.working_dir = self.adContext.config['working_dir']
        logging_module = SignalAdapter(self.signals.progress)
        self.adContext.ls.attach_logging_module(logging_module)
        self.adContext.prepare_ligand.attach_logging_module(logging_module)
        self.all_ligands = self.adContext.ligands

    def run(self):
        #adContext = self.adContext
        form = self.form
        ligands = self.ligands

        arg_dict = {}  # command options will be contained in this dictionary
        if form.checkBox_hydrogens.isChecked():
            arg_dict.update(A='checkhydrogens')

        for index, ligand_selection in enumerate(ligands):
            # Currently ligand_id and ligand.name are the same
            ligand_id = ligand_selection.text()
            ligand = self.all_ligands[ligand_id]
            ligand_pdb = self._update_ligand_pdb(ligand)
            # ligand_pdb = 'TEST_no_pdb_update'
            ligand_pdb_dir = os.path.dirname(ligand_pdb)
            ligand_pdbqt = os.path.join(self.working_dir, "ad_binding_test_ligand{}.pdbqt".format(ligand.name))
            ligand.pdbqt = ligand_pdbqt

            arg_dict.update(l=ligand_pdb, o=ligand_pdbqt)

            with while_in_dir(ligand_pdb_dir):  # because autodock can't see files in other directories ...

                try:
                    (rc, stdout, stderr) = self.adContext.prepare_ligand(**arg_dict)
                    # (rc, stdout, stderr) = adContext.ls('-l')
                except Exception as e:
                    s = str(e)
                    self.signals.error.emit(s)
                    self.signals.finished.emit('')

                # total_n = 1000
                # delay = random.random() / 100
                # for n in range(total_n):
                #     self.signals.progress.emit("Ligand {} working ... ".format(ligand.name))
                #     time.sleep(delay)
                #
                # self.signals.success.emit(ligand)

                if rc == 0:
                    self.signals.success.emit(ligand)
                else:
                    self.signals.error.emit(f'An error occurred while trying to prepare ligand {ligand.name}!')

        self.signals.finished.emit('Ran all ligands!')

    def _update_ligand_pdb(self, ligand):

        if ligand.fromPymol:
            ligand_pdb = os.path.join(self.working_dir, "ad_binding_test_ligand{}.pdb".format(ligand.name))
            self.signals.progress.emit("Generating pdb {} for ligand {}".format(ligand_pdb, ligand.name))
            ligand.pdb = ligand_pdb
            self.signals.pdb_update.emit(ligand)
            # try:
            #     cmd.save(ligand.pdb, ligand.name)
            # except cmd.QuietException:
            #     pass
        else:
            ligand_pdb = ligand.pdb

        return ligand_pdb

    # def run(self):
    #     total_n = 1000
    #     delay = random.random() / 100
    #     for n in range(total_n):
    #         self.signals.progress.emit("Ligand {} working ... ".format(self.ligand.name))
    #         time.sleep(delay)
    #
    #     self.signals.success.emit("Ligand {} done ... ".format(self.ligand.name))
