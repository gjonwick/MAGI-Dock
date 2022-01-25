from src.ADContext import ADContext
from pymol import cmd
import os
import logging
from src.Entities.Receptor import Receptor
from src.utils.util import dotdict
from src.utils.util import *

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
        adfr_path = adContext.config['adfr_path']
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