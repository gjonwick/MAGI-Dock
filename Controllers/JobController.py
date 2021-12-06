"""
Use this classes to delegate jobs, i.e. generate_receptors, prepare_ligands, etc.
You can also make these statics.
"""

from pymol.Qt import QtCore

from Models.ADContext import ADContext
from Models.Ligand import Ligand
from Models.Receptor import Receptor

from utils.util import dotdict

from subprocess import Popen, PIPE, STDOUT
import logging
import os
from pymol import cmd


class ReceptorJobController:

    def __init__(self, form, callbacks=None):
        self.form = form
        self.callbacks = callbacks

    def run(self):
        pass

    def generate(self):
        """ Generates pdbqt file for the receptor. """
        adContext = ADContext()
        form = self.form

        selection = form.sele_lstw.selectedItems()
        if len(selection) > 1:
            print('You can only have 1 receptor!')
            logging.error('You can only have 1 receptor!')
            return

        receptor_name = selection[0].text()

        WORK_DIR = os.getcwd()  # TODO: temporary
        prepare_receptor = 'prepare_receptor'
        receptor_path = os.path.join(WORK_DIR, f'TESTING_RECEPTOR_{receptor_name}.pdb')
        outputfile = os.path.join(WORK_DIR, f'TESTING_RECEPTOR_{receptor_name}.pdbqt')

        # try:
        #     cmd.save(receptor_path, receptor)
        # except cmd.QuietException:
        #     pass

        command = f'{prepare_receptor} -r {receptor_path} -o {outputfile} -A checkhydrogens'
        logging.info(command)

        # result, output = getStatusOutput(command)
        result = 0
        logging.info('Generating receptor ...')
        # print(output)

        if result == 0:
            receptor = Receptor(onReceptorAdded=self.callbacks['onReceptorAdded'])
            receptor.name = receptor_name
            receptor.pdbqt_location = outputfile
            adContext.addReceptor(receptor)

            logging.info(f'Success!')
            logging.info(f'Receptor pdbqt location = {adContext.receptor.pdbqt_location}')

        else:
            logging.error(f'Receptor {receptor_name} pdbqt file could not be generated!')
            # logging.error(output)

    def flexible(self):
        from pymol import stored
        """ Generates pdbqt files for the flexible receptor. """
        adContext = ADContext()
        form = self.form

        sele = form.sele_lstw.selectedItems()
        if len(sele) > 1:
            print('One selection at a time please!')
            logging.error('One selection at a time please!')
            return

        if adContext.receptor is None:
            logging.error('Please generate the receptor first!')
            return

        # TODO: encapsulate, get selected residues
        sele = sele[0].text()
        stored.flexible_residues = []
        cmd.iterate(sele + ' and name ca', 'stored.flexible_residues.append([chain, resn, resi])')
        print(str(stored.flexible_residues))
        chains = {}
        for chain, resn, resi in stored.flexible_residues:
            if resn not in ['ALA', 'GLY', 'PRO']:
                if chain in chains:
                    chains[chain].append(dotdict({'resn': resn, 'resi': resi}))
                else:
                    chains[chain] = [dotdict({'resn': resn, 'resi': resi})]

        # TODO: encapsulate, get loaded (loaded automatically into VinaCoupler when you click on it) receptor
        if adContext.receptor is not None:
            adContext.receptor.flexible_residues = chains
            adContext.setReceptor(
                adContext.receptor)  # trick the app into thinking that the receptor changed, in order to update the flexible listview(widget)

        res_string = adContext.receptor.flexibleResiduesAsString()
        logging.info(res_string)

        WORK_DIR = os.getcwd()  # TODO: temporary
        prepare_receptor = 'prepare_flexreceptor.py'
        # receptor_path = os.path.join(WORK_DIR, f'TESTING_RECEPTOR_{receptor}.pdb')
        receptor_pdbqt = adContext.receptor.pdbqt_location

        logging.info(f'Generating flexible residues ... {res_string}')

        command = f'{prepare_receptor} -r {receptor_pdbqt} -s {res_string}'
        logging.info(command)

        # result, output = getStatusOutput(command)
        result = 0
        # print(output)

        if result == 0:

            # TODO: autodock should return the names somewhere
            # check the paper
            rigid_receptor = receptor_pdbqt.split('.')[0] + '_rigid.pdbqt'
            flex_receptor = receptor_pdbqt.split('.')[0] + '_flex.pdbqt'

            adContext.receptor.rigid_pdbqt = rigid_receptor
            adContext.receptor.flex_pdbqt = flex_receptor

            # logging.debug(f'{output}')
            # for chain, contents in chains.items():
            #     for res in contents:
            #         form.flexRes_lstw.addItem(f'{chain} : {str(res.resn)}{str(res.resi)}')

            logging.info(f'Success generating flexible receptor with flexible residues {res_string}')
        else:
            logging.error(
                f'Generating receptor {adContext.receptor.name} with flexible residues {res_string} failed!')

        # form.flexRes_lstw.addItems(stored.flexible_residues)


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


"""
Vina Thread used to execute docking job
"""


class VinaWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal()
    progress = QtCore.pyqtSignal()

    def run(self):
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
