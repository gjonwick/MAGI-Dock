"""
MAGI-Dock

PyMOL Docking Box

An introduction about Widgets in Pymol can be found in the PyMol wiki,
Plugin tutorial ("Rendering Plugin" from Michael Lerner)

The following code uses the same library (pymol.Qt) which also provides direct access to
the additional features of PyQt5.

"""

# TODO: Fill the receptor and flexible residues lists before running the generation
# TODO: Recheck the default focuses on buttons
# then the user should be able to choose between receptors and flexibles


from __future__ import absolute_import
from __future__ import print_function

import os
import sys

# Avoid importing "expensive" modules here (e.g. scipy), since this code is
# executed on PyMOL's startup. Only import such modules inside functions.

sys.path.append(os.path.join(os.path.dirname(__file__)))
if '.' not in sys.path:
    sys.path.append('.')

print(sys.path)
print(sys.executable)

from src.Entities.Ligand import Ligand
from src.Entities.Receptor import Receptor

from src.ADContext import ADContext
from src.api.BoxAPI import BoxAPI

# from src.utils.util import dotdict

from src.api.LigandAPI import LigandJobController
from src.api.ReceptorAPI import RigidReceptorController, FlexibleReceptorController
from src.api.DockingAPI import VinaWorker, DockingJobController

from src.log.Logger import *

from pymol.cgo import *
from pymol import cmd

MODULE_UNLOADED = False
WORK_DIR = os.getcwd()


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
    # from pymol import stored

    cmd.set("auto_zoom", "off")

    # pymol.Qt provides the PyQt5 interface, but may support PyQt4
    # and/or PySide as well
    from pymol.Qt import QtWidgets
    from pymol.Qt import QtCore
    from pymol.Qt.utils import loadUi
    from pymol.Qt.utils import getSaveFileNameWithExt

    boxAPI = BoxAPI()
    adContext = ADContext()

    # create a new Window
    qDialog = QtWidgets.QDialog()
    saveTo = ''
    # AUTODOCK_PATH = '/home/jurgen/mgltools_x86_64Linux2_1.5.7/MGLToolsPckgs/AutoDockTools/Utilities24'

    # populate the Window from our *.ui file which was created with the Qt Designer
    uifile = os.path.join(os.path.dirname(__file__), 'demowidget.ui')
    form = loadUi(uifile, qDialog)

    adContext.setForm(form)

    logger = logging.getLogger(__name__)

    """ Multiple handlers can be created if you want to broadcast to many destinations. """
    log_box_handler = CustomWidgetLoggingHandler(form.plainTextEdit)
    log_box_handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))

    logger.addHandler(log_box_handler)
    logger.setLevel(logging.DEBUG)

    def log_to_widget(m):
        logger.info(m)

    def printRecChange():
        print(f'New receptor is{adContext.receptor.name}!')

    def onLoadedReceptorChanged():
        logger.info("Updating flexible list and loadedReceptor ... ")
        form.loadedReceptor_txt.setText(adContext.receptor.name)
        update_flexible_list()

    def onLigandChanged():
        form.ligands_lstw.clear()
        ligand_names = [lig_id for lig_id in adContext.ligands.keys()]
        form.ligands_lstw.addItems(ligand_names)

        logger.info("Updated ligand list widget!")

    def onPreparedLigandChange():
        """ Callback called when a ligand is added or prepared, or when a prepared_ligand is imported. Whenever there
        is an action with a ligand, this function is called, and if it happens that the ligand on which was acted
        is prepared, the corresponding units will respond. """
        form.preparedLigands_lstw.clear()
        form.preparedLigands_lstw_2.clear()
        prepared_ligands_names = [lig_id for lig_id in adContext.ligands.keys() if
                                  adContext.ligands[lig_id].isPrepared()]

        logger.debug(
            "onPreparedLigandChange() talking: List of prepared_ligands as observed by me is {}')"
            .format(prepared_ligands_names)
        )

        logger.info("Updated prepared ligands list widget!")

        form.preparedLigands_lstw.addItems(prepared_ligands_names)
        form.preparedLigands_lstw_2.addItems(prepared_ligands_names)

    def onReceptorAdded():
        update_receptor_list()

    def onLigandToDockChanged():
        pass

    adContext.register_callback(printRecChange)
    adContext.register_callback(onLoadedReceptorChanged)
    adContext.register_ligand_callback(onLigandChanged)
    adContext.register_ligand_callback(onPreparedLigandChange)

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

    if boxAPI.box_exists():
        boxConfig = boxAPI.box_data()
        updateCenterGUI(boxConfig.center.x, boxConfig.center.y, boxConfig.center.z)
        updateDimGUI(boxConfig.dim.x, boxConfig.dim.y, boxConfig.dim.z)

    ########################## <Callbacks> #############################

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
        # adContext.config['box_path'] = filename

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

        logger.info('Selections imported!')

    # ligand handler methods

    def OnAddLigandClicked():
        selected_ligands = form.sele_lstw_2.selectedItems()
        ligandController = LigandJobController(form)
        ligandController.add_ligands(selected_ligands)

        form.sele_lstw_2.clearSelection()

    def load_ligand():
        ligand_path = form.ligandPath_txt.text().strip()
        ligandController = LigandJobController(form)
        ligandController.load_ligand(ligand_path)

    def load_prepared_ligand():
        prepared_ligand_path = form.preparedLigand_txt.text().strip()
        ligandController = LigandJobController(form)
        ligandController.load_prepared_ligand(prepared_ligand_path)

    def load_receptor():
        receptor_pdb_path = form.receptorPath_txt.text().strip()
        if receptor_pdb_path.split('.')[1] != 'pdbqt':
            logger.info('The receptor must be in pdbqt format!')
            # return

        receptor_name = receptor_pdb_path.split('/')[-1].split('.')[0]

        receptor = Receptor(onReceptorAdded=onReceptorAdded)
        receptor.name = receptor_name
        receptor.fromPymol = False
        adContext.addReceptor(receptor)
        cmd.load(receptor_pdb_path, object=receptor_name)

    def remove_ligand():
        selection = form.ligands_lstw.selectedItems()
        ligandController = LigandJobController(form)
        ligandController.remove_ligands(selection)

    def update_receptor_list():
        form.receptor_lstw.clear()
        receptor_names = [rec_id for rec_id in adContext.receptors.keys()]
        form.receptor_lstw.addItems(receptor_names)
        # TODO: add tooltips here

    # TODO: the same as with OnDockingJobClicked, get the list of Entities here, and pass them to their respective
    #  controllers

    # Controller classes are initialized for each job, thus getting new loggers every instantiation
    # causing the log handlers to be "reloaded" (TODO: should be fixed in the future).
    #  Even though right now the Controllers are used as
    # "static" classes, the functionality may change in the future, so instantiating them for each run
    # is convenient right now. The same controllers used here, may be used for other actions on the entities.

    # NOTE: right here, by making controllers return messages on the task outcome, users can be notified
    # using "windows", "forms", etc.
    # i.e. result = rigidReceptor.run() or result = rigidReceptor.getResultMessage() and showPopUpDialog(result)

    def OnGenerateReceptorClicked():
        rigidReceptorController = RigidReceptorController(form, callbacks={'onReceptorAdded': onReceptorAdded})
        rigidReceptorController.run()

    def OnGenerateFlexibleClicked():
        flexibleReceptorController = FlexibleReceptorController(form)
        flexibleReceptorController.run()

    def OnPrepareLigandsClicked():
        ligandController = LigandJobController(form)
        ligandController.run()

    def OnRunDockingJobClicked():
        # Notify adContext about the ligands the user wishes to be docked
        selectedLigands = form.preparedLigands_lstw_2.selectedItems()
        for index, sele in enumerate(selectedLigands):
            ligand = adContext.ligands[sele.text()]
            adContext.ligands_to_dock[sele.text()] = ligand

        docking_job_controller = DockingJobController(form)
        docking_job_controller.run()

    # "button" callbacks
    def onSelectGeneratedReceptor(item):
        logger.info(f'Receptor {item.text()} selected')
        # adContext.receptor = adContext.receptors[item.text()]
        adContext.setReceptor(adContext.receptors[item.text()])
        # adContext.setRecTest(adContext.receptors[item.text()])
        # update_flexible_list() # TODO: refactor, on receptor_change (done)

    def onSelectLigandToDock(item):
        """ Sets ADContext ligand to dock (not useful right now, if multiple ligands supported) """
        adContext.setLigandToDock(adContext.ligands[item.text()])
        logger.info("Ligand to dock is: {} at {}".format(adContext.ligand_to_dock.name, adContext.ligand_to_dock.pdbqt))

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
        dir_name = str(QtWidgets.QFileDialog.getExistingDirectory(qDialog, "Select Directory"))
        adContext.config['adfr_path'] = dir_name
        logger.info(f'adfr_path = {dir_name}')
        form.adfrPath_txt.setText(dir_name)

    def OnBrowseMGLClicked():
        dir_name = str(QtWidgets.QFileDialog.getExistingDirectory(qDialog, "Select Directory"))
        adContext.config['mgl_path'] = dir_name
        logger.info(f'mgl_path = {dir_name}')
        form.mglPath_txt.setText(dir_name)

    def OnBrowseVinaClicked():
        dir_name = str(QtWidgets.QFileDialog.getExistingDirectory(qDialog, "Select Directory"))
        adContext.config['vina_path'] = dir_name
        logger.info(f'vina_path = {dir_name}')
        form.vinaPath_txt.setText(dir_name)

    def OnBrowseConfigClicked():
        filename = QtWidgets.QFileDialog.getOpenFileName(
            qDialog, 'Open', filter='All Files (*.*)'
        )

        if filename != ('', ''):
            form.configPath_txt.setText(filename[0])
            adContext.config['box_path'] = filename[0]
            logger.info(adContext.config['box_path'])

    def OnBrowseWorkingDirClicked():
        dir_name = str(QtWidgets.QFileDialog.getExistingDirectory(qDialog, "Select Directory"))
        adContext.config['working_dir'] = dir_name
        logger.info(f'working_dir = {dir_name}')
        form.workignDir_txt.setText(dir_name)

    def OnExhaustChange():
        adContext.config['dockingjob_params']['exhaustiveness'] = float(
            form.exhaust_txt.text().strip()) if form.exhaust_txt.text().strip().isnumeric() else 8
        logger.debug(f"Exhaust set to: {adContext.config['dockingjob_params']['exhaustiveness']}")

    # NOTE: doesn't change the environment of the application (i.e. executing cd will not change the current
    # directory, since that is controlled by the os module). Use the app shell, just for simple commands,
    # i.e. loading modules, checking the currentworking directory, etc.
    # The shell is not connected to the application state (TODO: to be considered in the future)
    def OnShellCommandSubmitted():
        import subprocess, traceback
        cmd = form.shellInput_txt.text()  # TODO: maybe a better way is to pass it as an argument
        # args = cmd.split(' ')
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

        try:
            out, err = p.communicate()
            rc = p.returncode

            if rc == 0:
                logger.info("Success!")
                logger.info(out.decode('utf-8'))
            else:
                logger.error(f"An error occurred executing: {cmd}")

        except Exception as e:
            logger.error(traceback.format_exc())

        form.shellInput_txt.clear()

    def onCloseWindow():
        cmd.delete('box')
        cmd.delete('axes')
        qDialog.close()

    def dummy():
        logger.debug('Callback works!')

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
    form.receptor_lstw.itemClicked.connect(onSelectGeneratedReceptor)
    # form.preparedLigands_lstw_2.itemClicked.connect(onSelectLigandToDock)
    # form.addLigandToDock_btn.clicked.connect(onAddLigandToDock)
    # form.removeLigandToDock_btn.clicked.connect(onRemoveLigandToDock)

    form.genReceptor_btn.clicked.connect(OnGenerateReceptorClicked)
    form.genFlexible_btn.clicked.connect(OnGenerateFlexibleClicked)
    form.genLigands_btn.clicked.connect(OnPrepareLigandsClicked)

    # form.sele_lstw_2.itemClicked(add_ligand)
    form.loadLigand_btn.clicked.connect(load_ligand)
    form.loadPreparedLigand_btn.clicked.connect(load_prepared_ligand)
    form.removeLigand_btn.clicked.connect(remove_ligand)
    form.addLigand_btn.clicked.connect(OnAddLigandClicked)
    form.loadLigand_btn.clicked.connect(load_ligand)
    form.loadReceptor_btn.clicked.connect(load_receptor)
    form.runDocking_btn.clicked.connect(OnRunDockingJobClicked)

    form.showBox_ch.stateChanged.connect(show_hide_Box)
    form.fillBox_ch.stateChanged.connect(fill_unfill_Box)

    form.importSele_btn.clicked.connect(import_sele)
    form.close_btn.clicked.connect(onCloseWindow)

    form.exhaust_txt.textChanged.connect(OnExhaustChange)

    form.browseADFR_btn.clicked.connect(OnBrowseADFRClicked)
    form.browseMGL_btn.clicked.connect(OnBrowseMGLClicked)
    form.browseVina_btn.clicked.connect(OnBrowseVinaClicked)
    form.browseConfig_btn.clicked.connect(OnBrowseConfigClicked)
    form.browseWorkDir_btn.clicked.connect(OnBrowseWorkingDirClicked)

    form.saveConfig_btn.clicked.connect(saveConfig)

    form.shellInput_txt.returnPressed.connect(OnShellCommandSubmitted)

    return qDialog
