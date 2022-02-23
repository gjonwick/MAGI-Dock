from pymol.Qt import QtCore
from src.ADContext import ADContext
import logging

from src.log.LoggingModule import SignalAdapter, LoggerAdapter
from src.utils.util import while_in_dir
from src.api.BaseController import BaseController
from typing import Any
import os


def get_pdbqt(ligand):
    return ligand.pdbqt


def run_flex_docking(ligands, receptor, output_file):
    pass


def run_rigid_docking(ligand, receptor, output_file):
    pass


class DockingJobController(BaseController):

    def __init__(self, form, multiple_ligand_docking=False, callbacks=None):
        super(DockingJobController, self).__init__(form, callbacks)
        self.multiple_ligand_docking = multiple_ligand_docking

    def _get_logger(self) -> Any:
        return self.loggerFactory \
            .giff_me_logger(name=__name__,
                            level=logging.DEBUG,
                            destination=self.form.dockingLogBox)

    def run(self):
        adContext = ADContext()
        # make sure tools are loaded; do the check here, because there's no point of calling the thread
        # if there is no tool to perform the job
        if not adContext.vina_tools_loaded:
            tools = adContext.load_vina_tools()
            if tools is None:
                self.logger.error('Vina tools could not be loaded! Please specify the correct path, or load the '
                                  'respective modules!')
                return

        form = self.form
        form.runDocking_btn.setEnabled(False)
        form.runMultipleDocking_btn.setEnabled(False)

        form.thread = QtCore.QThread()
        form.worker = VinaWorker(form, self.multiple_ligand_docking)
        form.worker.moveToThread(form.thread)
        form.thread.started.connect(form.worker.run)
        form.worker.finished.connect(form.thread.quit)
        form.worker.finished.connect(form.worker.deleteLater)
        # form.thread.finished.connect(form.thread.deleteLater)
        form.worker.finished.connect(self.onFinished)
        form.worker.progress.connect(lambda x: self.logger.info(x))

        # start thread
        form.thread.start()

        # form.thread.finished.connect(
        #     lambda: self.logger.info('Finish!')
        # )

    def onFinished(self, msg):
        self.form.runDocking_btn.setEnabled(True)
        self.form.runMultipleDocking_btn.setEnabled(True)
        self.logger.info(msg)
        # self.logger.info("I'm DONE!")

    def generateAffinityMaps(self, selectedLigands):
        """ Responsible for generating both gpf and affinity maps. """

        adContext = ADContext()
        receptor = adContext.receptor
        ligand_name = selectedLigands[0].text()
        ligand = adContext.ligands[ligand_name]

        if ligand.pdbqt is None:
            self.logger.error('The selected ligand is not prepared!')
            return

        adContext.prepare_gpf.attach_logging_module(LoggerAdapter(self.logger))
        adContext.autogrid.attach_logging_module(LoggerAdapter(self.logger))

        flex_docking = not len(receptor.flexible_residues) == 0

        if flex_docking:
            saved_receptor_name = receptor.rigid_pdbqt.split('.')[0]
        else:
            saved_receptor_name = receptor.pdbqt_location.split('.')[0]

        receptor_gpf = "{}.gpf".format(saved_receptor_name)  # full path here
        # In order for the receptor to "have" an gpf, it must be "associated" with a ligand.
        # Everytime we generate a gpf, the file is overridden "with" the new ligand. Rigid pdbqt will be used if
        # flexible docking.
        receptor_pdbqt = "{}.pdbqt".format(saved_receptor_name)  # receptor_pdbqt will be the rigid pdbqt if flexible

        try:
            (rc, stdout, stderr) = adContext.prepare_gpf(l=ligand.pdbqt, r=receptor_pdbqt, o=receptor_gpf,
                                                         y=True)
            if rc == 0:
                receptor.gpf = receptor_gpf
                self.logger.info("GPF for the {}_{} complex ready!".format(ligand.name, receptor.name))
            else:
                self.logger.error("Couldn't generate GPF for the {}_{} complex!".format(ligand.name, receptor.name))
                return

        except Exception as e:
            self.logger.error(repr(e))
            self.logger.error("An error occurred preparing gpf!")
            return

        receptor_pdbqt_dir = os.path.dirname(receptor_pdbqt)
        with while_in_dir(receptor_pdbqt_dir):
            try:
                (rc, stdout, stderr) = adContext.autogrid(p="{}.gpf".format(saved_receptor_name),
                                                          l="{}.glg".format(saved_receptor_name))
                if rc == 0:
                    self.logger.info("Affinity maps for the {}_{} complex ready!".format(ligand.name, receptor.name))
                else:
                    self.logger.error("Could not generate affinity maps for the {}_{} complex!".format(ligand.name,
                                                                                                       receptor.name))
            except Exception as e:
                self.logger.error(str(e))
                return


class VinaWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal(str)
    progress = QtCore.pyqtSignal(str)

    def __init__(self, form, multiple_ligands=False):
        super(VinaWorker, self).__init__()
        self.form = form
        self.arg_dict = {}
        self.default_args()
        self.multiple_ligands = multiple_ligands

    def default_args(self):
        adContext = ADContext()
        self.arg_dict.update(
            exhaustiveness=adContext.config['dockingjob_params']['exhaustiveness'],
            num_modes=adContext.config['dockingjob_params']['n_poses'],
            energy_range=adContext.config['dockingjob_params']['energy_range'],
            min_rmsd=adContext.config['dockingjob_params']['min_rmsd'],
            scoring=adContext.config['dockingjob_params']['scoring'],
            config=adContext.config['box_path']
        )

    def run(self):
        adContext = ADContext()
        logging_module = SignalAdapter(self.progress)
        adContext.vina.attach_logging_module(logging_module)
        # get working dir
        working_dir = adContext.config['working_dir']

        # make sure there are ligands to dock
        ligands_to_dock = adContext.ligands_to_dock
        if len(ligands_to_dock) < 1:
            self.finished.emit('There are no ligands to dock!')
            return

        receptor = adContext.receptor
        if receptor is None:
            self.finished.emit("No receptor loaded! Please generate and load the receptor first!")
            return

        """ When distinguishing between flexible or rigid, the receptor will make the difference. In the 
        case of multiple docking, each ligand will be run on flexible residues if the receptor has flexible residues. 
        If there are ligands to be run with rigid docking, than make sure there is another receptor with rigid residues. 
        """
        # TODO: add an arg_dict to make the command execution more readable
        with while_in_dir(working_dir):

            if len(ligands_to_dock) == 1:
                # basic docking
                ligand_to_dock = ligands_to_dock[list(ligands_to_dock.keys())[0]]

                # the case with ad4 scoring is different, handle it in a separate function
                if self.arg_dict['scoring'] == 'ad4':
                    arg_dict = self.ad_docking(ligand_to_dock, receptor)
                else:
                    # (rc, stdout, stderr) = self.basic_docking(ligand_to_dock, receptor)
                    arg_dict = self.basic_docking(ligand_to_dock, receptor)

            else:

                # batch docking
                # (rc, stdout, stderr) = self.batch_docking(ligands_to_dock, receptor)
                if self.multiple_ligands:
                    self.progress.emit('Preparing for multiple ligand docking ... ')
                    arg_dict = self.multiple_ligand_docking(ligands_to_dock, receptor)
                else:
                    self.progress.emit('Preparing for batch docking ... ')
                    arg_dict = self.batch_docking(ligands_to_dock, receptor)

            try:
                (rc, stdout, stderr) = adContext.vina(**arg_dict)
                self.progress.emit("return code = {}".format(rc))
                if rc == 0:
                    self.finished.emit("Success!")
                    # self.finished.emit(stdout.decode('utf-8'))
                else:
                    self.finished.emit("Failed!")
            except Exception as e:
                self.finished.emit(str(e))
                return

        self.finished.emit('Done :)')

    def ad_docking(self, ligand, receptor):
        arg_dict = self.arg_dict
        flex_docking = not len(receptor.flexible_residues) == 0
        try:
            receptor_maps_dir = os.path.dirname(receptor.gpf)
        except Exception as e:
            self.finished.emit(repr(e))
            return

        if flex_docking:
            rigid_receptor = receptor.rigid_pdbqt
            saved_rigid_receptor_name = receptor.rigid_pdbqt.split('/')[-1].split('.')[0]
            flex_receptor = receptor.flex_pdbqt
            if flex_receptor is not None and rigid_receptor is not None:
                output_file = "ad_vina_result_{}_flexible.pdbqt".format(receptor.name)
                with while_in_dir(receptor_maps_dir):
                    arg_dict.update(flex=flex_receptor,
                                    ligand=ligand.pdbqt,
                                    maps=saved_rigid_receptor_name,
                                    out=output_file)
        else:
            saved_receptor_name = receptor.pdbqt_location.split('/')[-1].split('.')[0]
            output_file = "ad_vina_result_{}.pdbqt".format(receptor.name)
            with while_in_dir(receptor_maps_dir):
                arg_dict.update(ligand=ligand.pdbqt,
                                maps=saved_receptor_name,
                                out=output_file)

        return arg_dict

    def basic_docking(self, ligand, receptor):
        """ Function responsible for preparing the options to run docking with only 1 ligand. """

        arg_dict = self.arg_dict
        flex_docking = not len(receptor.flexible_residues) == 0

        if flex_docking:
            rigid_receptor = receptor.rigid_pdbqt
            flex_receptor = receptor.flex_pdbqt
            if flex_receptor is not None and rigid_receptor is not None:
                output_file = "vina_result_{}_flexible.pdbqt".format(receptor.name)
                arg_dict.update(receptor=rigid_receptor,
                                flex=flex_receptor,
                                ligand=ligand.pdbqt,
                                out=output_file)
            else:
                self.system.finished("When running flexible docking please generate the flexible receptor first!")
                return
        else:
            output_file = "vina_result_{}.pdbqt".format(receptor.name)
            arg_dict.update(receptor=receptor.pdbqt_location,
                            ligand=ligand.pdbqt,
                            out=output_file)
        return arg_dict

    # TODO: vinardo and ad4 scoring functions currently do not work in batch docking
    def batch_docking(self, ligands_to_dock, receptor):
        """ Function responsible for preparing the options to run docking in batch mode. """

        arg_dict = self.arg_dict
        ligands_pdbqt = list(map(get_pdbqt, list(ligands_to_dock.values())))
        self.progress.emit(str(ligands_pdbqt))

        flex_docking = not len(receptor.flexible_residues) == 0

        if flex_docking:
            rigid_receptor = receptor.rigid_pdbqt
            flex_receptor = receptor.flex_pdbqt
            if flex_receptor is not None and rigid_receptor is not None:
                output_dir = "vina_batch_result_{}_flexible".format(receptor.name)
                if not os.path.isdir(output_dir):
                    os.mkdir(output_dir)
                arg_dict.update(receptor=rigid_receptor,
                                flex=flex_receptor,
                                batch=ligands_pdbqt,
                                dir=output_dir)
            else:
                self.system.finished("When running flexible docking please generate the flexible receptor first!")
                return
        else:
            output_dir = "vina_batch_result_{}".format(receptor.name)
            if not os.path.isdir(output_dir):
                os.mkdir(output_dir)
            arg_dict.update(receptor=receptor.pdbqt_location,
                            batch=ligands_pdbqt,
                            dir=output_dir)
        return arg_dict

    def multiple_ligand_docking(self, ligands_to_dock, receptor):

        """
        Traceback (most recent call last):
        File "/home/u3701/.pymol/startup/MAGI-Dock/src/api/DockingAPI.py", line 108, in run
            self.finished.emit(e)
        TypeError: VinaWorker.finished[str].emit(): argument 1 has unexpected type 'TypeError'
    
        """

        """ Function responsible for running docking with multiple ligands. """
        # self.logger.error("Multiple ligand docking not implemented yet!")
        adContext = ADContext()

        arg_dict = self.arg_dict
        flex_docking = not len(receptor.flexible_residues) == 0
        ligands_pdbqt = list(map(get_pdbqt, list(ligands_to_dock.values())))
        self.progress.emit(str(ligands_pdbqt))

        if flex_docking:
            rigid_receptor = receptor.rigid_pdbqt
            flex_receptor = receptor.flex_pdbqt
            if flex_receptor is not None and rigid_receptor is not None:
                output_file = "vina_multidock_result_{}_flexible.pdbqt".format(receptor.name)
                arg_dict.update(receptor=rigid_receptor,
                                flex=flex_receptor,
                                ligand=ligands_pdbqt,
                                out=output_file)
            else:
                self.finished.emit("No flex and rigid parts!")
                return
        else:
            output_file = "vina_multidock_result_{}.pdbqt".format(receptor.name)
            arg_dict.update(receptor=receptor.pdbqt_location,
                            ligand=ligands_pdbqt,
                            out=output_file)

        return arg_dict

# sample_command = f'vina --receptor {rigid_receptor} \ --flex {flex_receptor} --ligand {
# ligand_to_dock.pdbqt} \ --config {box_path} \ --exhaustiveness {exhaustiveness} --out
# TESTING_DOCK_{receptor.name}_vina_out.pdbqt'
