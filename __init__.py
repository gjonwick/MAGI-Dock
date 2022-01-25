'''
PyMOL Docking Box

An introduction about Widgets in Pymol can be found in the PyMol wiki, 
Plugin tutorial ("Rendering Plugin" from Michael Lerner)

The following code uses the same library (pymol.Qt) which also provides direct access to 
the additional features of PyQt5.

'''

# TODO: Fill the receptor and flexible residues lists before running the generation
# then the user should be able to choose between receptors and flexibles

# TODO: observer pattern, to broadcast the state of the box to every textfield

from __future__ import absolute_import
from __future__ import print_function

# Avoid importing "expensive" modules here (e.g. scipy), since this code is
# executed on PyMOL's startup. Only import such modules inside functions.

import os
import sys

from src.ADContext import ADContext
from src.Controllers.BoxAPI import BoxAPI
from src.utils.util import dotdict

sys.path.append(os.path.join(os.path.dirname(__file__)))
from src.dependencies import *

print(TESTIMPORT)
import logging
from pymol.cgo import *
from pymol import cmd

MODULE_UNLOADED = False
WORK_DIR = os.getcwd()

CONFIG = dotdict({
    'vina_path': None,
    'autodock_path': None,
    'box_path': None
})


def getStatusOutput(command):
    from subprocess import Popen, PIPE, STDOUT
    env = dict(os.environ)
    args = command.split()
    if args[0].endswith('.py') and MODULE_UNLOADED:
        args.insert(0, sys.executable)
    p = Popen(args, stdout=PIPE, stderr=STDOUT, stdin=PIPE, env=env)
    print(args)
    output = p.communicate()[0]
    return p.returncode, output


# TODO: move this functions to utils

class CustomLogger(logging.Handler):

    def __init__(self, logBox) -> None:
        super().__init__()
        self.widget = logBox
        self.widget.setReadOnly(True)

    def emit(self, record):
        msg = self.format(record)
        self.widget.appendPlainText(msg)

    def write(self, m):
        pass


# NOTE: test
class pymolAPI:

    def __init__(self) -> None:
        pass

    def load_cgo(self):
        return

    def save_selection(self):
        return

    def get_selection(self):
        return

    def get_boundaries(self):
        return


def __init_plugin__(app=None):
    """
    Add an entry to the PyMOL "Plugin" menu
    """
    from pymol.plugins import addmenuitemqt

    addmenuitemqt('Docking Box', run_plugin_gui)


# global reference to avoid garbage collection of our dialog
dialog = None


def run_plugin_gui():
    """
    Open our custom dialog
    """
    global dialog

    if dialog is None:
        dialog = make_dialog()

    dialog.show()


def make_dialog():
    # entry point to PyMOL's API
    #from pymol import stored

    cmd.set("auto_zoom", "off")

    # pymol.Qt provides the PyQt5 interface, but may support PyQt4
    # and/or PySide as well
    from pymol.Qt import QtWidgets
    from pymol.Qt import QtOpenGL
    from pymol.Qt import QtCore
    from pymol.Qt.utils import loadUi
    from pymol.Qt.utils import getSaveFileNameWithExt

    class ViewPort(QtOpenGL.QGLWidget):
        def __init__(self, parent=None):
            QtOpenGL.QGLWidget.__init__(self, parent)
            self.setMinimumSize(640, 480)

        def paintGL(self):
            QtOpenGL.glClear(QtOpenGL.GL_COLOR_BUFFER_BIT | QtOpenGL.GL_DEPTH_BUFFER_BIT)
            QtOpenGL.glLoadIdentity()
            QtOpenGL.glTranslatef(-2.5, 0.5, -6.0)
            QtOpenGL.glColor3f(1.0, 1.5, 0.0)
            QtOpenGL.glPolygonMode(QtOpenGL.GL_FRONT, QtOpenGL.GL_FILL)
            QtOpenGL.glBegin(QtOpenGL.GL_TRIANGLES)
            QtOpenGL.glVertex3f(2.0, -1.2, 0.0)
            QtOpenGL.glVertex3f(2.6, 0.0, 0.0)
            QtOpenGL.glVertex3f(2.9, -1.2, 0.0)
            QtOpenGL.glEnd()
            QtOpenGL.glFlush()

        def initializeGL(self):
            QtOpenGL.glClearDepth(1.0)
            QtOpenGL.glDepthFunc(QtOpenGL.GL_LESS)
            QtOpenGL.glEnable(QtOpenGL.GL_DEPTH_TEST)
            QtOpenGL.glShadeModel(QtOpenGL.GL_SMOOTH)
            QtOpenGL.glMatrixMode(QtOpenGL.GL_PROJECTION)
            QtOpenGL.glLoadIdentity()
            QtOpenGL.gluPerspective(45.0, 1.33, 0.1, 100.0)
            QtOpenGL.glMatrixMode(QtOpenGL.GL_MODELVIEW)

    boxAPI = BoxAPI()
    adContext = ADContext()
    # viewport = ViewPort()
    # create a new Window
    qDialog = QtWidgets.QDialog()
    saveTo = ''
    # AUTODOCK_PATH = '/home/jurgen/mgltools_x86_64Linux2_1.5.7/MGLToolsPckgs/AutoDockTools/Utilities24'

    # populate the Window from our *.ui file which was created with the Qt Designer
    uifile = os.path.join(os.path.dirname(__file__), 'demowidget.ui')
    form = loadUi(uifile, qDialog)

    adContext.setForm(form)

    logger = CustomLogger(form.plainTextEdit)
    logger.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(logger)
    logging.getLogger().setLevel(logging.INFO)

    def log_to_widget(m):
        logging.info(m)

    def printRecChange():
        print(f'New receptor is{adContext.receptor.name}!')

    def onLoadedReceptorChanged():
        logging.info("Updating flexible list and loadedReceptor ... ")
        form.loadedReceptor_txt.setText(adContext.receptor.name)
        update_flexible_list()

    def onLigandChanged():
        form.ligands_lstw.clear()
        ligand_names = [lig_id for lig_id in adContext.ligands.keys()]
        form.ligands_lstw.addItems(ligand_names)
        onPreparedLigandChange()

    def onPreparedLigandChange():

        form.preparedLigands_lstw.clear()
        form.preparedLigands_lstw_2.clear()
        prepared_ligands_names = [lig_id for lig_id in adContext.ligands.keys() if
                                  adContext.ligands[lig_id].isPrepared()]
        for lig_id in adContext.ligands.keys():
            logging.info(lig_id)

        form.preparedLigands_lstw.addItems(prepared_ligands_names)
        form.preparedLigands_lstw_2.addItems(prepared_ligands_names)

    def onReceptorAdded():
        update_receptor_list()

    def onLigandToDockChanged():
        pass

    adContext.register_callback(printRecChange)
    adContext.register_callback(onLoadedReceptorChanged)
    adContext.register_ligand_callback(onLigandChanged)

    # adContext.add_callback(onLigandToDockAdded, '_ligandondock_callbacks')

    def updateCenterGUI(x, y, z):
        form.centerX.setValue(x)
        form.centerY.setValue(y)
        form.centerZ.setValue(z)

    def updateDimGUI(x, y, z):
        form.dimX.setValue(x)
        form.dimY.setValue(y)
        form.dimZ.setValue(z)

    def updateGUIdata():
        boxData = boxAPI.box_data()
        updateCenterGUI(boxData.center.x, boxData.center.y, boxData.center.z)
        updateDimGUI(boxData.dim.x, boxData.dim.y, boxData.dim.z)

    def __broadcast():
        return

    if boxAPI.box_exists():
        boxConfig = boxAPI.box_data()
        updateCenterGUI(boxConfig.center.x, boxConfig.center.y, boxConfig.center.z)
        updateDimGUI(boxConfig.dim.x, boxConfig.dim.y, boxConfig.dim.z)

    ########################## <Callbacks> #############################
    # TODO: add increment step option
    def update():
        if boxAPI.box_exists():
            centerX = form.centerX.value()
            centerY = form.centerY.value()
            centerZ = form.centerZ.value()
            dimX = form.dimX.value()
            dimY = form.dimY.value()
            dimZ = form.dimZ.value()

            boxAPI.set_center(centerX, centerY, centerZ)
            boxAPI.set_dim(dimX, dimY, dimZ)

    def gen_box():
        selection = form.selection_txt.text().strip() if form.selection_txt.text() != '' else '(sele)'
        boxAPI.gen_box(selection=selection)
        updateGUIdata()

    def get_config():
        filename = form.config_txt.text() if form.config_txt.text() != '' else "config.txt"
        boxAPI.read_box(filename)
        updateGUIdata()

    def save_config():
        vinaout = form.vinaoutput.text()
        boxAPI.save_box("config.txt", vinaout)
        # boxAPI.saveBox(saveTo)

    # TODO: add save functionality
    def saveAs_config():
        filename = getSaveFileNameWithExt(
            qDialog, 'Save As...', filter='All Files (*.*)'
        )
        global saveTo
        saveTo = filename
        vinaout = form.vinaoutput.text() if form.vinaoutput.text() != '' else 'result'
        boxAPI.save_box(filename, vinaout)
        #adContext.config['box_path'] = filename

    def browse():
        # filename = getSaveFileNameWithExt(
        #     dialog, 'Open', filter='All Files (*.*)'
        # )
        filename = QtWidgets.QFileDialog.getOpenFileName(
            qDialog, 'Open', filter='All Files (*.*)'
        )
        if filename != ('', ''):
            form.config_txt.setText(filename[0])

    def browse_ligands():
        filename = QtWidgets.QFileDialog.getOpenFileName(
            qDialog, 'Open', filter='All Files (*.*)'
        )

        if filename != ('', ''):
            form.ligandPath_txt.setText(filename[0])

    def browse_receptors():
        filename = QtWidgets.QFileDialog.getOpenFileName(
            qDialog, 'Open', filter='All Files (*.*)'
        )

        if filename != ('', ''):
            form.receptorPath_txt.setText(filename[0])

    def browse_prepared_ligands():
        filename = QtWidgets.QFileDialog.getOpenFileName(
            qDialog, 'Open', filter='All Files (*.*)'
        )

        if filename != ('', ''):
            form.preparedLigand_txt.setText(filename[0])

    def show_hide_Box():
        if form.showBox_ch.isChecked():
            boxAPI.show_box()
            form.centerX.setDisabled(False)
            form.centerY.setDisabled(False)
            form.centerZ.setDisabled(False)
            form.dimX.setDisabled(False)
            form.dimY.setDisabled(False)
            form.dimZ.setDisabled(False)
        else:
            boxAPI.hide_box()
            form.centerX.setDisabled(True)
            form.centerY.setDisabled(True)
            form.centerZ.setDisabled(True)
            form.dimX.setDisabled(True)
            form.dimY.setDisabled(True)
            form.dimZ.setDisabled(True)

    def fill_unfill_Box():
        if form.fillBox_ch.isChecked():
            boxAPI.fill()
        else:
            boxAPI.unfill()

    def updateStepSize():
        step_size = form.step_size.value()
        form.centerX.setSingleStep(step_size)
        form.centerY.setSingleStep(step_size)
        form.centerZ.setSingleStep(step_size)
        form.dimX.setSingleStep(step_size)
        form.dimY.setSingleStep(step_size)
        form.dimZ.setSingleStep(step_size)

    # TODO: make an observer
    def import_sele():
        # NOTE: using a listwidget for the selections view, because it is a higher level class, inheriting from
        # ListView. Use ListView if you want greater customization.
        selections = cmd.get_names("selections") + cmd.get_names()
        if 'axes' in selections:
            selections.remove('axes')
        if 'box' in selections:
            selections.remove('box')

        form.sele_lstw.clear()
        form.sele_lstw.addItems(selections)

        form.sele_lstw_2.clear()
        form.sele_lstw_2.addItems(selections)

        logging.info('Selections imported!')

    # ligand handler methods

    def add_ligand():
        selection = form.sele_lstw_2.selectedItems()
        logging.debug(selection)
        for index, sele in enumerate(selection):
            ligand = Ligand(sele.text(), '', onPrepared=onPreparedLigandChange)
            adContext.addLigand(ligand)

        print(adContext.ligands)
        form.sele_lstw_2.clearSelection()

    def load_ligand():
        ligand_pdb_path = form.ligandPath_txt.text().strip()

        if ligand_pdb_path.split('.') == 'pdbqt':
            logging.info(f'PDBQTs not accepted here!')
            # return

        ligand_name = ligand_pdb_path.split('/')[-1].split('.')[0]

        ligand = Ligand(ligand_name, ligand_pdb_path, onPrepared=onPreparedLigandChange)
        ligand.fromPymol = False
        adContext.addLigand(ligand)
        cmd.load(ligand_pdb_path, object=ligand_name)

    def load_prepared_ligand():
        prepared_ligand_path = form.preparedLigand_txt.text().strip()
        prepared_ligand_name = prepared_ligand_path.split('/')[-1].split('.')[0]

        ligand = Ligand(prepared_ligand_name, '')
        ligand.pdbqt = prepared_ligand_path
        ligand.fromPymol = False
        ligand.prepared = True
        adContext.addLigand(ligand)
        cmd.load(prepared_ligand_path, object=prepared_ligand_name)

    def load_receptor():
        receptor_pdb_path = form.receptorPath_txt.text().strip()
        if receptor_pdb_path.split('.')[1] != 'pdbqt':
            logging.info('The receptor must be in pdbqt format!')
            # return

        receptor_name = receptor_pdb_path.split('/')[-1].split('.')[0]

        receptor = Receptor(onReceptorAdded=onReceptorAdded)
        receptor.name = receptor_name
        receptor.fromPymol = False
        adContext.addReceptor(receptor)
        cmd.load(receptor_pdb_path, object=receptor_name)

    def remove_ligand():
        selection = form.ligands_lstw.selectedItems()
        for index, item in enumerate(selection):
            adContext.removeLigand(item.text())
            # TODO: remove foreign ligand from pymol if you want

    def update_receptor_list():
        form.receptor_lstw.clear()
        receptor_names = [rec_id for rec_id in adContext.receptors.keys()]
        form.receptor_lstw.addItems(receptor_names)
        # TODO: add tooltips here

    # TODO: async
    def generate_receptor():
        receptorController = ReceptorJobController(form, callbacks={'onReceptorAdded': onReceptorAdded})
        receptorController.generate()

    # TODO: async
    def generate_flexible():
        receptorController = ReceptorJobController(form)
        receptorController.flexible()

    def prepare_ligands():
        ligandController = LigandJobController(form)
        ligandController.prepare()

    def run_docking_job():
        form.thread = QtCore.QThread()
        form.worker = VinaWorker()
        form.worker.moveToThread(form.thread)
        form.thread.started.connect(form.worker.run)
        form.worker.finished.connect(form.thread.quit)
        form.worker.finished.connect(form.worker.deleteLater)
        form.thread.finished.connect(form.thread.deleteLater)
        form.worker.progress.connect(lambda: logging.info('Working ... '))

        # start thread
        form.thread.start()

        # final resets
        form.runDocking_btn.setEnabled(False)
        form.thread.finished.connect(
            lambda: form.runDocking_btn.setEnabled(True)
        )

        form.thread.finished.connect(
            lambda: logging.info('Finish!')
        )


    def run_docking_job_test():
        adContext = ADContext()  # NOTE: DANGEROUS (ADContext not yet thread safe)
        box_path = adContext.config['box_path']

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
                                           --exhaustiveness 32 --out TESTING_DOCK_{receptor.name}_vina_out.pdbqt'
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

    def onCloseWindow():
        cmd.delete('box')
        cmd.delete('axes')
        qDialog.close()

    # "button" callbacks
    def onSelectReceptor(item):
        logging.info(f'Receptor {item.text()} selected')
        # adContext.receptor = adContext.receptors[item.text()]
        adContext.setReceptor(adContext.receptors[item.text()])
        # adContext.setRecTest(adContext.receptors[item.text()])
        # update_flexible_list() # TODO: refactor, on receptor_change (done)

    def onSelectLigandToDock(item):
        """ Sets ADContext ligand to dock (not useful right now, if multiple ligands supported) """
        adContext.setLigandToDock(adContext.ligands[item.text()])
        logging.info(f'Ligand to dock is: {adContext.ligand_to_dock.name} at {adContext.ligand_to_dock.pdbqt}')

    def OnSelectRunDockingJob():
        selectedLigands = form.preparedLigands_lstw_2.selectedItems()
        for index, sele in enumerate(selectedLigands):
            ligand = adContext.ligands[sele.text()]
            adContext.ligands_to_dock[sele.text()] = ligand

        run_docking_job_test()



    def update_flexible_list():
        form.flexRes_lstw.clear()
        flexibles = adContext.receptor.flexible_residues
        if len(flexibles) != 0:
            for chain, contents in flexibles.items():
                for res in contents:
                    form.flexRes_lstw.addItem(f'{chain} : {str(res.resn)}{str(res.resi)}')

    def fill_test():
        boxAPI.fill()

    def saveConfig():
        adfrPath = form.adfrPath_txt.text()
        mglPath = form.mglPath_txt.text()
        vinaPath = form.vinaPath_txt.text()
        configPath = form.configPath_txt.text()
        adContext.config['adfr'] = adfrPath
        adContext.config['mglPath'] = mglPath
        adContext.config['vinaPath'] = vinaPath
        adContext.config['configPath'] = configPath


    def OnBrowseADFRClicked():
        filename = QtWidgets.QFileDialog.getOpenFileName(
            qDialog, 'Open', filter='All Files (*.*)'
        )
        if filename != ('', ''):
            form.adfrPath_txt.setText(filename[0])
            adContext.config['adfr_path'] = filename[0]
            logging.info(adContext.config['adfr_path'])

    def OnBrowseMGLClicked():
        filename = QtWidgets.QFileDialog.getOpenFileName(
            qDialog, 'Open', filter='All Files (*.*)'
        )
        if filename != ('', ''):
            form.mglPath_txt.setText(filename[0])
            adContext.config['mgl_path'] = filename[0]
            logging.info(adContext.config['mgl_path'])

    def OnBrowseVinaClicked():
        filename = QtWidgets.QFileDialog.getOpenFileName(
            qDialog, 'Open', filter='All Files (*.*)'
        )
        if filename != ('', ''):
            form.vinaPath_txt.setText(filename[0])
            adContext.config['vina_path'] = filename[0]
            logging.info(adContext.config['vina_path'])

    def OnBrowseConfigClicked():
        filename = QtWidgets.QFileDialog.getOpenFileName(
            qDialog, 'Open', filter='All Files (*.*)'
        )

        if filename != ('', ''):
            form.configPath_txt.setText(filename[0])
            adContext.config['box_path'] = filename[0]
            logging.info(adContext.config['box_path'])

    def dummy():
        pass

    ########################## </Callbacks> #############################

    # bind callbacks
    form.centerX.valueChanged.connect(update)
    form.centerY.valueChanged.connect(update)
    form.centerZ.valueChanged.connect(update)
    form.dimX.valueChanged.connect(update)
    form.dimY.valueChanged.connect(update)
    form.dimZ.valueChanged.connect(update)
    form.step_size.valueChanged.connect(updateStepSize)
    form.getConfig_btn.clicked.connect(get_config)
    form.save_btn.clicked.connect(save_config)
    form.saveAs_btn.clicked.connect(saveAs_config)
    form.browse_btn.clicked.connect(browse)
    form.browseLigand_btn.clicked.connect(browse_ligands)
    form.browseReceptor_btn.clicked.connect(browse_receptors)
    form.browsePreparedLigand_btn.clicked.connect(browse_prepared_ligands)
    form.genBox_btn.clicked.connect(gen_box)
    form.receptor_lstw.itemClicked.connect(onSelectReceptor)
    # form.preparedLigands_lstw_2.itemClicked.connect(onSelectLigandToDock)
    # form.addLigandToDock_btn.clicked.connect(onAddLigandToDock)
    # form.removeLigandToDock_btn.clicked.connect(onRemoveLigandToDock)

    form.genReceptor_btn.clicked.connect(generate_receptor)
    form.genFlexible_btn.clicked.connect(generate_flexible)
    form.genLigands_btn.clicked.connect(prepare_ligands)

    # form.sele_lstw_2.itemClicked(add_ligand)
    form.loadLigand_btn.clicked.connect(load_ligand)
    form.loadPreparedLigand_btn.clicked.connect(load_prepared_ligand)
    form.removeLigand_btn.clicked.connect(remove_ligand)
    form.addLigand_btn.clicked.connect(add_ligand)
    form.loadLigand_btn.clicked.connect(load_ligand)
    form.loadReceptor_btn.clicked.connect(load_receptor)
    form.runDocking_btn.clicked.connect(OnSelectRunDockingJob)

    form.showBox_ch.stateChanged.connect(show_hide_Box)
    form.fillBox_ch.stateChanged.connect(fill_unfill_Box)

    form.importSele_btn.clicked.connect(import_sele)
    form.close_btn.clicked.connect(onCloseWindow)

    form.browseADFR_btn.clicked.connect(OnBrowseADFRClicked)
    form.browseMGL_btn.clicked.connect(OnBrowseMGLClicked)
    form.browseVina_btn.clicked.connect(OnBrowseVinaClicked)
    form.browseConfig_btn.clicked.connect(OnBrowseConfigClicked)

    form.saveConfig_btn.clicked.connect(saveConfig)

    return qDialog


actions = {}
