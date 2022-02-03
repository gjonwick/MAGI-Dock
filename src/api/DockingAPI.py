from pymol.Qt import QtCore
from src.ADContext import ADContext
import logging
from src.utils.util import while_in_dir
from src.api.BaseController import BaseController
from typing import Any


class DockingJobController(BaseController):

    def __init__(self, form, callbacks=None):
        super(DockingJobController, self).__init__(form, callbacks)

    def _get_logger(self) -> Any:
        return self.loggerFactory \
            .giff_me_logger(name=__name__,
                            level=logging.DEBUG,
                            destination=self.form.dockingLogBox)

    def run(self):
        form = self.form
        form.runDocking_btn.setEnabled(False)

        form.thread = QtCore.QThread()
        form.worker = VinaWorker(form)
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
        self.logger.info(msg)
        # self.logger.info("I'm DONE!")


class VinaWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal(str)
    progress = QtCore.pyqtSignal(str)

    def __init__(self, form):
        super(VinaWorker, self).__init__()
        self.form = form

    def run(self):
        adContext = ADContext()

        # get working dir
        working_dir = adContext.config['working_dir']

        # make sure tools are loaded
        if not adContext.vina_tools_loaded:
            tools = adContext.load_vina_tools()
            if tools is None:
                self.finished.emit('Vina tools could not be loaded! Please specify the correct path, or load the '
                                   'respective modules!')
                return

        # make sure there are ligands to dock
        ligands_to_dock = adContext.ligands_to_dock
        if len(ligands_to_dock) < 1:
            self.finished.emit('There are no ligands to dock!')
            return

        with while_in_dir(working_dir):
            if len(ligands_to_dock) == 1:
                # basic docking
                ligand_to_dock = ligands_to_dock[list(ligands_to_dock.keys())[0]]
                self.basic_docking(ligand_to_dock)
            else:
                # batch docking
                self.multiple_ligand_docking(ligands_to_dock)

        # # ligands_to_dock = adContext.ligands_to_dock
        #
        # # ligands_to_dock = ['str'] # NOTE: vina probably supports batch docking with multiple ligands
        # # ligand = adContext.ligands['str']
        # # prefix = '/'.join(receptor.pdbqt_location.split('/')[0:-1])
        # # suffix = receptor.pdbqt_location.split('/')[-1]
        # # name = '_'.join(suffix.split('.')[0].split('_')[0:-1])
        #
        # # for stdout_line in p.stdout.readlines():
        # #     self.progress.emit(stdout_line)
        # #     sys.stdout.flush()
        # # form.plainTextEdit.moveCursor(QtGui.QTextCursor.End)
        # # p.stdout.close()

        self.finished.emit('DOne :)')

    # TODO: should VinaWorker log? HELL NO, just emit
    def basic_docking(self, ligand):
        adContext = ADContext()  # NOTE: (ADContext not yet thread safe)
        flex_docking = True

        # get the entities
        receptor = adContext.receptor

        if receptor is None:
            self.finished.emit("No receptor loaded! Please generate and load the receptor first!")
            return

        if len(receptor.flexible_residues) == 0:
            flex_docking = False

        if flex_docking:
            rigid_receptor = receptor.rigid_pdbqt
            flex_receptor = receptor.flex_pdbqt
            if flex_receptor is not None and rigid_receptor is not None:
                # output_file = f'vina_result_{receptor.name}_flexible.pdbqt'
                output_file = "vina_result_{}_flexible.pdbqt".format(receptor.name)
                (rc, stdout, stderr) = adContext.vina(receptor=rigid_receptor,
                                                      flex=flex_receptor,
                                                      ligand=ligand.pdbqt,
                                                      config=adContext.config['box_path'],
                                                      exhaustiveness=adContext.config['dockingjob_params'][
                                                          'exhaustiveness'],
                                                      out=output_file)

            else:
                # self.logger.error('An error occurred while processing rigid and flexible structures!')
                self.finished.emit('An error occurred while processing rigid and flexible structures!')
                return
        else:
            # output_file = f'vina_result_{receptor.name}.pdbqt'
            output_file = "vina_result_{}.pdbqt".format(receptor.name)
            (rc, stdout, stderr) = adContext.vina(receptor=receptor.pdbqt_location,
                                                  ligand=ligand.pdbqt,
                                                  config=adContext.config['box_path'],
                                                  exhaustiveness=adContext.config['dockingjob_params'][
                                                      'exhaustiveness'],
                                                  out=output_file)

        if rc == 0:
            self.finished.emit(f'Docking job completed successfully. The poses can be loaded from {output_file}')
        else:
            pass

    def multiple_ligand_docking(self, ligands_to_dock):
        """ TODO """
        # self.logger.error("Multiple ligand docking not implemented yet!")
        return

# sample_command = f'vina --receptor {rigid_receptor} \ --flex {flex_receptor} --ligand {
# ligand_to_dock.pdbqt} \ --config {box_path} \ --exhaustiveness {exhaustiveness} --out
# TESTING_DOCK_{receptor.name}_vina_out.pdbqt'
