'''
PyMOL Docking Box

An introduction about Widgets in Pymol can be found in the PyMol wiki, 
Plugin tutorial ("Rendering Plugin" from Michael Lerner)

The following code uses the same library (pymol.Qt) which also provides direct access to 
the additional features of PyQt5.

'''

#TODO: Fill the receptor and flexible residues lists before running the generation
# then the user should be able to choose between receptors and flexibles

#TODO: observer pattern, to broadcast the state of the box to every textfield

from __future__ import absolute_import
from __future__ import print_function
import enum

# Avoid importing "expensive" modules here (e.g. scipy), since this code is
# executed on PyMOL's startup. Only import such modules inside functions.

import os
import sys
import logging
from pymol.cgo import *                                                                                     
from pymol import cmd      
from pymol.vfont import plain
from pymol.viewing import center, show  
from pymol import stored

MODULE_UNLOADED = False
WORK_DIR = os.getcwd()

# TODO: move this functions to utils

def touch(filename):
    with open(filename, 'a'):
        pass

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

class vec3:

    def __init__(self, x, y, z) -> None:
        self.x = x
        self.y = y
        self.z = z

    def __add__(self, v) -> 'vec3':
        return vec3(self.x + v.x, self.y + v.y, self.z + v.z)

    def __sub__(self, v) -> 'vec3':
        return vec3(self.x - v.x, self.y - v.y, self.z - v.z)

    def __mul__(self, c) -> 'vec3':
        return vec3(self.x * c, self.y * c, self.z * c)

    def dot(self, v: 'vec3') -> float:
        return self.x * v.x + self.y * v.y + self.z * v.z

    def cross(self, v: 'vec3') -> 'vec3':
        return vec3(self.y * v.z - self.z * v.y, self.z * v.x - self.x * v.z, self.x * v.y - self.y * v.x)
    
    def __truediv__(self, c) -> 'vec3':
        return vec3(self.x / c, self.y / c, self.z / c)

    def __str__(self):
        return f'({str(self.x)}, {str(self.y)}, {str(self.z)})'

    def cube(self, x: float) -> float:
        return x * x * x

    def unpack(self):
        return self.x, self.y, self.z

class dotdict(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


# NOTE: Rendering includes communication with pymol (cmd, etc.). May be decoupled from the Box class
# because it is better to let the plugin handle the rendering and the communication with PyMol
# we can let the box just return CGO objects maybe?
class Box_s:

    class __Box:
        def __init__(self) -> None:
            self.center = None
            self.dim = None
            self.fill = False
            self.hidden = False

        def __str__(self):
            return f'Center {str(self.center)}); Dim {str(self.dim)}'


        def setFill(self, state):
            self.fill = state

        def setHidden(self, state):
            self.hidden = state

        def setConfig(self, center : 'vec3', dim : 'vec3') -> None:
            self.center = center
            self.dim = dim

        def translate(self, v : 'vec3') -> None:
            self.center = self.center + v
        
        def extend(self, v : 'vec3') -> None:
            self.dim = self.dim + v
        
        def setCenter(self, v : 'vec3') -> None:
            self.center = v
        
        def getCenter(self) -> 'vec3':
            return self.center

        def setDim(self, v : 'vec3') -> None:
            self.dim = v
        
        def getDim(self)-> 'vec3':
            return self.dim
        

        def __line(p1, p2):
            x1, y1, z1 = p1
            x2, y2, z2 = p2
            return [CYLINDER, float(x1), float(y1), float(z1), float(x2), float(y2), float(z2), 0.25, 1, 1, 1, 1, 1, 1]

        def __showaxes(self, minX : float, minY : float, minZ : float) -> None:
            cmd.delete('axes')
            w = 0.15 # cylinder width 
            l = 5.0 # cylinder length

            obj = [
                CYLINDER, minX, minY, minZ, minX + l, minY, minZ, w, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0,
                CYLINDER, minX, minY, minZ, minX, minY + l, minZ, w, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0,
                CYLINDER, minX, minY, minZ, minX, minY, minZ + l, w, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0,
                CONE,   minX + l, minY, minZ, minX + 1 + l, minY, minZ, w * 1.5, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 
                CONE, minX,   minY + l, minZ, minX, minY + 1 + l, minZ, w * 1.5, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 
                CONE, minX, minY,   minZ + l, minX, minY, minZ + 1 + l, w * 1.5, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0
            ]

            cyl_text(obj,plain,[minX + l + 1 + 0.2, minY, minZ - w],'X',0.1,axes=[[1,0,0],[0,1,0],[0,0,1]])
            cyl_text(obj,plain,[minX - w, minY + l + 1 + 0.2 , minZ],'Y',0.1,axes=[[1,0,0],[0,1,0],[0,0,1]])
            cyl_text(obj,plain,[minX-w, minY, minZ + l + 1 + 0.2],'Z',0.1,axes=[[1,0,0],[0,1,0],[0,0,1]])

            cmd.load_cgo(obj,'axes')
        
        def __refresh(self) -> None:
            center = self.center
            dim = self.dim
            (minX, minY, minZ) = (center - dim / 2).unpack()
            (maxX, maxY, maxZ) = (center + dim / 2).unpack()

            box_cgo = [
                        LINEWIDTH, float(2.0),

                        BEGIN, LINES,
                        COLOR, float(0.5), float(0.8), float(1.0),

                        VERTEX, minX, minY, minZ,       #1
                        VERTEX, minX, minY, maxZ,       #2

                        VERTEX, minX, maxY, minZ,       #3
                        VERTEX, minX, maxY, maxZ,       #4

                        VERTEX, maxX, minY, minZ,       #5
                        VERTEX, maxX, minY, maxZ,       #6

                        VERTEX, maxX, maxY, minZ,       #7
                        VERTEX, maxX, maxY, maxZ,       #8


                        VERTEX, minX, minY, minZ,       #1
                        VERTEX, maxX, minY, minZ,       #5

                        VERTEX, minX, maxY, minZ,       #3
                        VERTEX, maxX, maxY, minZ,       #7

                        VERTEX, minX, maxY, maxZ,       #4
                        VERTEX, maxX, maxY, maxZ,       #8

                        VERTEX, minX, minY, maxZ,       #2
                        VERTEX, maxX, minY, maxZ,       #6


                        VERTEX, minX, minY, minZ,       #1
                        VERTEX, minX, maxY, minZ,       #3

                        VERTEX, maxX, minY, minZ,       #5
                        VERTEX, maxX, maxY, minZ,       #7

                        VERTEX, minX, minY, maxZ,       #2
                        VERTEX, minX, maxY, maxZ,       #4

                        VERTEX, maxX, minY, maxZ,       #6
                        VERTEX, maxX, maxY, maxZ,       #8

                        END
                ]

            self.__showaxes(minX, minY, minZ)
            cmd.delete('box')
            cmd.load_cgo(box_cgo, 'box')

        def render(self) -> None:
            if self.hidden == False and self.center != None and self.dim != None:
                self.__refresh()
    
    _instance = None

    def __init__(self):
        if not Box_s._instance:
            Box_s._instance = Box_s.__Box() 

    # Delegate Calls to the inner private class
    def __getattr__(self, name):
        return getattr(self._instance, name)


# TODO: IMPORTANT! add coupling between vinaInstance receptors and listWidget

class VinaCoupler:

    class __VinaCoupler:

        def __init__(self)-> None:
            self.receptor = None
            self.ligands = {}
            self.receptors = {}
            self.form = None

        def setForm(self, form):
            self.form = form

        def setFlexibleResidues(self, residues):
            self.flexibleResidues = residues

        def setReceptor(self, receptor):
            self.receptor = receptor

        def setLigands(self, ligands):
            self.ligands = ligands
        
        def addLigand(self, ligand):
            self.ligands[ligand.name] = ligand
        
        def removeLigand(self, id):
            self.ligands.pop(id, None)
        
        # def addReceptor(self, receptor : 'Receptor'):
        #     self.receptor[receptor.name] = receptor
        #     self.loadReceptor(receptor.name)

        def generateReceptor(self):
            
            return

        # def loadReceptor(self, receptor):
        #     self.form.receptor_lstw.addItem(receptor)
        #     return

            #return getStatusOutput(command)
        
        def generateFlexibleResidues(self):
            #residues = self.receptor.getResidues()

            return
    
    _instance = None

    def __init__(self):
        if not VinaCoupler._instance:
            VinaCoupler._instance = VinaCoupler.__VinaCoupler()
        
    # Delegate calls
    def __getattr__(self, name):
        return getattr(self._instance, name)


'''
    attributes:
        selection
        name - should act as an unique identifier (ID)
        pdbqt_location - the path to the generated/to be generated pdbqt file of the receptor
        flexible_residues - a list (dictionary) of the flexible residues of the receptor
'''

class Receptor:

    
    def __init__(self) -> None:
        self.selection = None
        self.name = None
        self.pdbqt_location = None
        self.flexible_path = None
        self.flexible_residues = {}

    def flexibleResiduesAsString(self):
        print(f'Receptor says: my location is {str(self.pdbqt_location)}')
        res_str = ''
        pid = os.path.basename(self.pdbqt_location).split('.')[0]
        if '_' in pid:
                pid = pid.split('_')[-1]

        chains = []
        full_res_string = ''
        for chain, contents in self.flexible_residues.items():            
            ress = []
            chain_string = f'{pid}:{chain}:'
            for res in contents:
                #full_res_name = pid + ':' + chain + ':' + '_'.join(ress)
                res_string = f'{str(res.resn) + res.resi}'
                ress.append(res_string)
            #TODO: review this, flex_receptor doesn't accept it
            full_res_string = '_'.join(ress)
            chain_string = chain_string + full_res_string

            chains.append(chain_string)
        
        final_str = ','.join(chains)

        logging.info(final_str)
        # NOTE: should return final_string
        return full_res_string


class Ligand:

    def __init__(self, name, pdb) -> None:
        self.name = name
        self.pdb = pdb
        self.pdbqt = ''
        self.fromPymol = True

    def prepare(self):

        # if self.fromPymol:
        #     self.pdb  = os.path.join(WORK_DIR, f'TESTING_LIGAND_{self.name}.pdb')
        #     try:
        #         cmd.save(self.pdb , self.name)
        #     except cmd.QuietException:
        #         pass
        # else:
        #     pass
        
        # self.pdbqt = os.path.join(WORK_DIR, f'TESTING_LIGAND_{self.name}.pdbqt')
        pass

class bAPI:

    def __init__(self) -> None:
        self.gBox = Box_s()

    def extend(self, x, y, z):
        self.gBox.extend(vec3(x, y, z))
        self.gBox.render()

    def move(self, x, y, z):
        self.gBox.translate(vec3(x, y, z))
        self.gBox.render()

    def setCenter(self, x, y, z):
        self.gBox.setCenter(vec3(x, y, z))
        self.gBox.render()
        print(self.gBox)

    def setDim(self, x, y, z):
        self.gBox.setDim(vec3(x, y, z))
        self.gBox.render()
        print(self.gBox)

    # TODO: Decouple generation from returning the data?

    def genBox(self, selection="(sele)", padding=2.0, linewidth=2.0, r=1.0, g=1.0, b=1.0) -> 'dotdict':
        ([minX, minY, minZ],[maxX, maxY, maxZ]) = cmd.get_extent(selection)
        # cmd.iterate(selector.process(selection, 'stored.residues.add(resv'))
        # for residue in stored.residues:
        #     print(str(residue))
        center = vec3((minX + maxX) / 2, (minY + maxY) / 2, (minZ + maxZ) / 2)
        dim = vec3((maxX - minX + 2 * padding), (maxY - minY + 2 * padding), (maxZ - minZ + 2 * padding))
        self.gBox.setConfig(center, dim)
        print(self.gBox)
        self.gBox.render()
        return self.boxData()

    def readBox(self, filename) -> 'dotdict':
        with open(filename, 'r') as f:
            lines = f.readlines()
            
            centerX = float(lines[0].split('=')[1].strip())
            centerY = float(lines[1].split('=')[1].strip())
            centerZ = float(lines[2].split('=')[1].strip())

            dimX = float(lines[3].split('=')[1].strip())
            dimY = float(lines[4].split('=')[1].strip())
            dimZ = float(lines[5].split('=')[1].strip())

            center = vec3(centerX, centerY, centerZ)
            dim = vec3(dimX, dimY, dimZ)
        
        self.gBox.setConfig(center, dim)
        print(self.gBox)
        self.gBox.render()  
        return self.boxData()    

    def saveBox(self, filename, vinaoutput):
        gBox = self.gBox
        with open(filename, 'w') as f:
            f.write("center_x = " + str(gBox.center.x) + '\n')
            f.write("center_y = " + str(gBox.center.y) + '\n')
            f.write("center_z = " + str(gBox.center.z) + '\n')

            f.write("size_x = " + str(gBox.dim.x) + '\n')
            f.write("size_y = " + str(gBox.dim.y) + '\n')
            f.write("size_z = " + str(gBox.dim.z) + '\n')

            f.write("out = " + vinaoutput + '\n')
            

    # TODO: handle the case when the name changes
    # Explicit function to render and hide the box (why not?)
    def renderBox(self):
        self.gBox.render()

    def hideBox(self):
        self.gBox.setHidden(True)
        cmd.delete('box')
        cmd.delete('axes')

    def showBox(self):
        self.gBox.setHidden(False)
        self.gBox.render()

    def boxData(self) -> 'dotdict':
        gBox = self.gBox

        if not self.boxExists():
            raise Exception("No box config yet!")

        return dotdict({
            "center" : dotdict({
                "x" : gBox.getCenter().x,
                "y" : gBox.getCenter().y,
                "z" : gBox.getCenter().z
            }),
            "dim" : dotdict({
                "x" : gBox.getDim().x,
                "y" : gBox.getDim().y,
                "z" : gBox.getDim().z
            })
        })

    def boxExists(self) -> bool:
        return self.gBox.getCenter() != None and self.gBox.getDim() != None

# NOTE: test
class pymolAPI:
    
    def __init__(self) -> None:
        pass

    def renderBox():
        return
    
    def saveSelection():
        return

    def getSelections():
        return

    def getBoundaries():
        return


def __init_plugin__(app=None):
    '''
    Add an entry to the PyMOL "Plugin" menu
    '''
    from pymol.plugins import addmenuitemqt
    
    

    # ## Can be removed ##
    # from boxAPI import dotdict
    # from boxAPI import vec3
    # ## Can be removed ##

    addmenuitemqt('Docking Box', run_plugin_gui)


# global reference to avoid garbage collection of our dialog
dialog = None


def run_plugin_gui():
    '''
    Open our custom dialog
    '''
    global dialog

    if dialog is None:
        dialog = make_dialog()

    dialog.show()

def make_dialog():
    
    # entry point to PyMOL's API
    from pymol import stored

    cmd.set("auto_zoom", "off")

    # pymol.Qt provides the PyQt5 interface, but may support PyQt4
    # and/or PySide as well
    from pymol.Qt import QtWidgets
    from pymol.Qt.utils import loadUi
    from pymol.Qt.utils import getSaveFileNameWithExt

    #import boxAPI
    boxAPI = bAPI()
    vinaInstance = VinaCoupler()
    # create a new Window
    dialog = QtWidgets.QDialog()
    saveTo = ''
    #AUTODOCK_PATH = '/home/jurgen/mgltools_x86_64Linux2_1.5.7/MGLToolsPckgs/AutoDockTools/Utilities24'

    # populate the Window from our *.ui file which was created with the Qt Designer
    uifile = os.path.join(os.path.dirname(__file__), 'demowidget.ui')
    form = loadUi(uifile, dialog)
    vinaInstance.setForm(form)
    
    logger = CustomLogger(form.plainTextEdit)
    logger.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(logger)
    logging.getLogger().setLevel(logging.INFO)
    
    def updateCenterGUI(x, y, z):
        form.centerX.setValue(x)
        form.centerY.setValue(y)
        form.centerZ.setValue(z)
    
    def updateDimGUI(x, y, z):
        form.dimX.setValue(x)
        form.dimY.setValue(y)
        form.dimZ.setValue(z)

    def updateGUIdata():
        boxData = boxAPI.boxData()
        updateCenterGUI(boxData.center.x, boxData.center.y, boxData.center.z)
        updateDimGUI(boxData.dim.x, boxData.dim.y, boxData.dim.z)

    def __broadcast():
        return

    if boxAPI.boxExists():
        boxConfig = boxAPI.boxData()
        updateCenterGUI(boxConfig.center.x, boxConfig.center.y, boxConfig.center.z)
        updateDimGUI(boxConfig.dim.x, boxConfig.dim.y, boxConfig.dim.z)

    

    ########################## <Callbacks> #############################
    # TODO: add increment step option
    def update():
        if boxAPI.boxExists():
            centerX = form.centerX.value()
            centerY = form.centerY.value()
            centerZ = form.centerZ.value()
            dimX = form.dimX.value()
            dimY = form.dimY.value()
            dimZ = form.dimZ.value()

            boxAPI.setCenter(centerX, centerY, centerZ)
            boxAPI.setDim(dimX, dimY, dimZ)
    
    
    def gen_box():
        selection = form.selection_txt.text().strip() if form.selection_txt.text() != '' else '(sele)'
        boxAPI.genBox(selection=selection)
        updateGUIdata()

    def get_config():
        filename = form.config_txt.text() if form.config_txt.text() != '' else "config.txt"
        boxAPI.readBox(filename)
        updateGUIdata()

    def save_config():
        vinaout = form.vinaoutput.text() if form.vinaoutput.text() != '' else 'result'  
        boxAPI.saveBox("config.txt", vinaout)
        #boxAPI.saveBox(saveTo)

    # TODO: add save functionality
    def saveAs_config():
        filename = getSaveFileNameWithExt(
            dialog, 'Save As...', filter='All Files (*.*)'
        )
        global saveTo
        saveTo = filename
        vinaout = form.vinaoutput.text() if form.vinaoutput.text() != '' else 'result'
        boxAPI.saveBox(filename, vinaout)   

    def browse():
        # filename = getSaveFileNameWithExt(
        #     dialog, 'Open', filter='All Files (*.*)'
        # )
        filename = QtWidgets.QFileDialog.getOpenFileName(
            dialog, 'Open', filter='All Files (*.*)'
        )
        if filename != ('', ''):
            form.config_txt.setText(filename[0])
    
    def browse_ligands():
        filename = QtWidgets.QFileDialog.getOpenFileName(
            dialog, 'Open', filter='All Files (*.*)'
        )

        if filename != ('', ''):
            form.ligandPath_txt.setText(filename[0])

           

    def show_hide_Box():
        if form.showBox_ch.isChecked():
            boxAPI.showBox()
            form.centerX.setDisabled(False)
            form.centerY.setDisabled(False)
            form.centerZ.setDisabled(False)
            form.dimX.setDisabled(False)
            form.dimY.setDisabled(False)
            form.dimZ.setDisabled(False)
        else:
            boxAPI.hideBox()
            form.centerX.setDisabled(True)
            form.centerY.setDisabled(True)
            form.centerZ.setDisabled(True)
            form.dimX.setDisabled(True)
            form.dimY.setDisabled(True)
            form.dimZ.setDisabled(True)

        print(f'State of the box = {str(boxAPI.gBox.hidden)}')
        logging.info(f'State of the box = {str(boxAPI.gBox.hidden)}')

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
    def update_ligands_list():
        form.ligands_lstw.clear()
        ligand_names = [lig_id for lig_id in vinaInstance.ligands.keys()]
        form.ligands_lstw.addItems(ligand_names)
    
    def add_ligand():
        selection = form.sele_lstw_2.selectedItems()
        logging.debug(selection)
        for index, sele in enumerate(selection):
            ligand = Ligand(sele.text(), '')
            vinaInstance.addLigand(ligand)

        print(vinaInstance.ligands)
        form.sele_lstw_2.clearSelection()
        update_ligands_list()

    def load_ligand():
        ligand_pdb_path = form.ligandPath_txt.text().strip()
        ligand_name = ligand_pdb_path.split('/')[-1].split('.')[0]

        ligand = Ligand(ligand_name, ligand_pdb_path)
        ligand.fromPymol = False
        vinaInstance.addLigand(ligand)

        update_ligands_list()
        
    def remove_ligand():
        selection = form.ligands_lstw.selectedItems()
        for index, item in enumerate(selection):
            vinaInstance.removeLigand(item.text())

        update_ligands_list()

    # async
    '''
    Generates pdbqt file for the receptor.

    '''
    def generate_receptor():
        selection = form.sele_lstw.selectedItems()
        if len(selection) > 1:
            print('You can only have 1 receptor!')
            logging.error('You can only have 1 receptor!')
            return
        
        rec = Receptor()
        vinaInstance.setReceptor(rec)
        receptor = selection[0].text()
        vinaInstance.receptor.name = receptor
        
        WORK_DIR = os.getcwd() # TODO: temporary
        prepare_receptor = 'prepare_receptor'
        receptor_path = os.path.join(WORK_DIR, f'TESTING_RECEPTOR_{receptor}.pdb')
        outputfile = os.path.join(WORK_DIR, f'TESTING_RECEPTOR_{receptor}.pdbqt')
        
        try:
            cmd.save(receptor_path, receptor)
        except cmd.QuietException:
            pass

        command = f'{prepare_receptor} -r {receptor_path} -o {outputfile} -A checkhydrogens' 
        logging.info(command)

        result, output = getStatusOutput(command)
        
        logging.info('Generating receptor ...')
        print(output)

        if result == 0:
            vinaInstance.receptor.pdbqt_location = outputfile
            # NOTE: right now only 1 receptor is supported
            form.receptor_lstw.clear()
            form.receptor_lstw.addItem(receptor)
            logging.info(f'Success!')
            logging.info(f'Receptor pdbqt location = {vinaInstance.receptor.pdbqt_location}')

        else:
            logging.error(f'Receptor {receptor} pdbqt file could not be generated!')
            logging.error(output)
    
    # async
    def generate_flexible():
        sele = form.sele_lstw.selectedItems()
        if len(sele) > 1:
            print('One selection at a time please!')
            logging.error('One selection at a time please!')
            return
        
        if vinaInstance.receptor == None:
            logging.error('Please generate the receptor first!')
            return

        sele = sele[0].text()    
        stored.flexible_residues = []
        cmd.iterate(sele + ' and name ca', 'stored.flexible_residues.append([chain, resn, resi])')
        print(str(stored.flexible_residues))
        chains = {}
        for chain, resn, resi in stored.flexible_residues:
            if resn not in ['ALA', 'GLY', 'PRO']:
                if chain in chains:
                    chains[chain].append(dotdict({'resn' : resn, 'resi': resi}))
                else:
                    chains[chain] = [dotdict({'resn' : resn, 'resi': resi})]

        if vinaInstance.receptor != None:
            vinaInstance.receptor.flexible_residues = chains

        res_string = vinaInstance.receptor.flexibleResiduesAsString()
        logging.info(res_string)

        WORK_DIR = os.getcwd() # TODO: temporary
        prepare_receptor = 'prepare_flexreceptor.py'
        #receptor_path = os.path.join(WORK_DIR, f'TESTING_RECEPTOR_{receptor}.pdb')
        receptor_pdbqt = vinaInstance.receptor.pdbqt_location
        
        logging.info(f'Generating flexible residues ... {res_string}')

        command = f'{prepare_receptor} -r {receptor_pdbqt} -s {res_string}' 
        logging.info(command)

        result, output = getStatusOutput(command)

        print(output)

        if result == 0:
            
            logging.debug(f'{output}')        
            for chain, contents in chains.items():
                for res in contents:
                    form.flexRes_lstw.addItem(f'{chain} : {str(res.resn)}{str(res.resi)}')
                
            logging.info(f'Success generating flexible receptor with flexible residues {res_string}')
        else:
            logging.error(f'Generating receptor {vinaInstance.receptor.name} with flexible residues {res_string} failed!')
        
        #form.flexRes_lstw.addItems(stored.flexible_residues)
      


    # async
    '''
    Generates pdbqt files for the ligands
    
    1. save the molecule as pdb
    2. run prepare ligand to generate pdbqt
    '''
    #TODO: use the ligand fromPymol flag to distinguish which ligand to choose (the one from the file, or the one from pymol)
    def prepare_ligands():
        
        SUCCESS_FLAG = True

        ligand_selection = form.ligands_lstw.selectedItems()

        WORK_DIR = os.getcwd() # TODO: temporary

        prep_command = 'prepare_ligand'

        for index, ligand_selection in enumerate(ligand_selection):
            ligand_name = ligand_selection.text()
            ligand = vinaInstance.ligands[ligand_name]
            if ligand.fromPymol:
                ligand_pdb = os.path.join(WORK_DIR, f'TESTING_LIGAND_{ligand_name}.pdb')
                ligand.pdb = ligand_pdb
                try:
                    cmd.save(ligand_pdb, ligand_name)
                except cmd.QuietException:
                    pass
            # else:
            #     ligand_pdb = ligand.pdb
            
            ligand_pdbqt = os.path.join(WORK_DIR, f'TESTING_LIGAND_{ligand_name}.pdbqt')
            ligand.pdbqt = ligand_pdbqt

            command = f'{prep_command} -l {ligand_pdb} -o {ligand_pdbqt}'

            result, output = getStatusOutput(command)

            if result == 0:
                logging.debug(output)

                #ligand.pdbqt = ligand_pdbqt
                form.preparedLigands_lstw.addItem(ligand.name)
                logging.info(f'Ligand {ligand.name} pdbqt generated at {ligand.pdbqt}')
            else:
                logging.info(f'An error occurred while trying to prepare the ligand ...')
                logging.info(output)
    
    def onCloseWindow():
        cmd.delete('box')
        cmd.delete('axes')
        dialog.close()

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
    form.genBox_btn.clicked.connect(gen_box)

    form.genReceptor_btn.clicked.connect(generate_receptor)
    form.genFlexible_btn.clicked.connect(generate_flexible)
    form.genLigands_btn.clicked.connect(prepare_ligands)

    #form.sele_lstw_2.itemClicked(add_ligand)
    form.loadLigand_btn.clicked.connect(load_ligand)
    form.removeLigand_btn.clicked.connect(remove_ligand)
    form.addLigand_btn.clicked.connect(add_ligand)
    form.loadLigand_btn.clicked.connect(load_ligand)

    form.showBox_ch.stateChanged.connect(show_hide_Box)
    form.importSele_btn.clicked.connect(import_sele)
    form.close_btn.clicked.connect(onCloseWindow)

    return dialog


actions = {}