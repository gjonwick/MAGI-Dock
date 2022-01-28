from pymol.Qt import QtCore
from src.ADContext import ADContext
from subprocess import Popen
import logging

"""
Vina Thread used to execute docking job
"""


class VinaWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal()
    progress = QtCore.pyqtSignal()

    def run(self):
        adContext = ADContext()  # NOTE: (ADContext not yet thread safe)

        box_path = adContext.config['box_path']
        vina_path = adContext.config['vina_path']
        dockingjob_params = adContext.config['dockingjob_params']
        exhaustiveness = dockingjob_params['exhaustiveness']


        receptor = adContext.receptor
        rigid_receptor = receptor.rigid_pdbqt
        flex_receptor = receptor.flex_pdbqt
        # ligand_to_dock = adContext.ligand_to_dock

        ligands_to_dock = adContext.ligands_to_dock
        sample_command = ''
        if len(ligands_to_dock) == 1:
            ligand_to_dock = ligands_to_dock[list(ligands_to_dock.keys())[0]]
            sample_command = f'vina --receptor {rigid_receptor} \
                                   --flex {flex_receptor} --ligand {ligand_to_dock.pdbqt} \
                                   --config {box_path} \
                                   --exhaustiveness {exhaustiveness} --out TESTING_DOCK_{receptor.name}_vina_out.pdbqt'

        else:
            # batch dock
            pass

        # ligands_to_dock = adContext.ligands_to_dock

        # ligands_to_dock = ['str'] # NOTE: vina probably supports batch docking with multiple ligands
        # ligand = adContext.ligands['str']
        # prefix = '/'.join(receptor.pdbqt_location.split('/')[0:-1])
        # suffix = receptor.pdbqt_location.split('/')[-1]
        # name = '_'.join(suffix.split('.')[0].split('_')[0:-1])

        adContext.dockcommand = sample_command
        args = sample_command.split()
        print(f'Executing {args}')

        p = Popen(args, shell=False)
        self.progress.emit()
        # for stdout_line in p.stdout.readlines():
        #     self.progress.emit(stdout_line)
        #     sys.stdout.flush()
        # form.plainTextEdit.moveCursor(QtGui.QTextCursor.End)
        # p.stdout.close()

        # (out, err) = p.communicate()
        logging.info(sample_command)

        self.finished.emit()
