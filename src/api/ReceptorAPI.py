from src.ADContext import ADContext
from pymol import cmd
from src.Entities.Receptor import Receptor
from src.log.LoggingModule import LoggerAdapter
from src.utils.util import *
from src.log.Logger import *
from src.api.BaseController import BaseController


class RigidReceptorController(BaseController):

    def __init__(self, form, callbacks=None):
        super(RigidReceptorController, self).__init__(form, callbacks)

    def _get_logger(self) :
        return self.loggerFactory\
                   .giff_me_logger(name=__name__,
                                   level=logging.DEBUG,
                                   destination=self.form.receptorLogBox)

    def run(self):
        adContext = ADContext()
        self.logger.info('Im running fine!')
        # TODO: (future issue) remove form reference from here; better if the API classes do not know about the form
        form = self.form
        selection = form.sele_lstw.selectedItems()
        if len(selection) > 1:
            print('You can only have 1 receptor!')
            self.logger.error('You can only have 1 receptor!')
            return

        receptor_name = selection[0].text()

        working_dir = adContext.config['working_dir']

        receptor_pdb = os.path.join(working_dir, f'ad_binding_test_{receptor_name}.pdb')
        receptor_pdbqt = os.path.join(working_dir, f'ad_binding_test_{receptor_name}.pdbqt')

        # Better to not use adContext.ad_tools_loaded, in order to distinguish between init load, or couldn't load
        if not adContext.ad_tools_loaded:
            tools = adContext.load_ad_tools()
            if tools is None:
                self.logger.error(
                    'Could not load AutoDock tools! Please specify the paths, or load the respective modules!')
                return

        # os.path.expanduser("~")
        with while_in_dir(working_dir):

            try:
                cmd.save(receptor_pdb, receptor_name)
            except cmd.QuietException:
                pass

            """ Alternative way, here ADContext is responsible for running the ad module commands
                and for checking if the config is ok. """
            adContext.prepare_receptor.attach_logging_module(LoggerAdapter(self.logger))
            (rc, stdout, stderr) = adContext.prepare_receptor(r=receptor_pdb, o=receptor_pdbqt)
            print(f'Return code = {rc}')
            self.logger.debug(f"Return code = {rc}")

            if stdout is not None:
                self.logger.debug(f"{stdout}") #.decode('utf-8')

            if rc == 0:
                receptor = Receptor(onReceptorAdded=self.callbacks['onReceptorAdded'])
                receptor.name = receptor_name
                receptor.pdbqt_location = receptor_pdbqt
                adContext.addReceptor(receptor)
                self.logger.info(f'Receptor pdbqt generated at: {adContext.receptor.pdbqt_location}')
            else:
                self.logger.error(f'Failed generating receptor {receptor_name}!')


class FlexibleReceptorController(BaseController):

    def __init__(self, form, callbacks=None):
        super(FlexibleReceptorController, self).__init__(form, callbacks)

    def _get_logger(self):
        return self.loggerFactory.giff_me_logger(name=__name__, level=logging.DEBUG, destination=self.form.receptorLogBox)

    def run(self):
        from pymol import stored
        """ Generates pdbqt files for the flexible receptor. """
        adContext = ADContext()
        form = self.form
        self.logger.info('Im running fine!')
        sele = form.sele_lstw.selectedItems()
        # TODO: make it a popup
        if len(sele) > 1:
            print('One selection at a time please!')
            self.logger.error('One selection at a time please!')
            return

        if not adContext.ad_tools_loaded:
            tools = adContext.load_ad_tools()
            if tools is None:
                self.logger.error(
                    'Could not load AutoDock tools! Please specify the paths, or load the respective modules!')
                return

        if adContext.receptor is None:
            self.logger.error('Please generate the receptor first!')
            return

        # XXX: there was an error trying to generate only 1 flexible residue
        # TODO: encapsulate, get selected residues
        sele = sele[0].text()
        stored.flexible_residues = []
        cmd.iterate(sele + ' and name ca', 'stored.flexible_residues.append([chain, resn, resi])')
        # print(str(stored.flexible_residues))
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
            # receptor is already set, now you just reset it

        """ In the pymol session the flexible residues will have already
        been assigned to the receptor. If the program fails to generate the 
        respective (pdbqt) files, then the receptor and its flexible
        residues will still be 'cached' in the session, and ready to be rerun. """

        working_dir = adContext.config['working_dir']

        with while_in_dir(working_dir):

            res_string = adContext.receptor.flexibleResiduesAsString()
            receptor_pdbqt = adContext.receptor.pdbqt_location

            prepare_receptor = 'prepare_flexreceptor.py'
            # receptor_path = os.path.join(WORK_DIR, f'TESTING_RECEPTOR_{receptor}.pdb')

            self.logger.info(f'Generating flexible residues ... {res_string}')
            print(f'Generating flexible residues ... {res_string}')

            adContext.prepare_flexreceptor.attach_logging_module(LoggerAdapter(self.logger))
            (rc, stdout, stderr) = adContext.prepare_flexreceptor(r=receptor_pdbqt, s=res_string)
            # command = f'{prepare_receptor} -r {receptor_pdbqt} -s {res_string}'
            # result, output = getStatusOutput(command)
            if stdout is not None:
                self.logger.debug(f"{stdout}") # .decode('utf-8')

            if rc == 0:

                # TODO: autodock should return the names somewhere
                # check the paper
                rigid_receptor = receptor_pdbqt.split('.')[0] + '_rigid.pdbqt'
                flex_receptor = receptor_pdbqt.split('.')[0] + '_flex.pdbqt'

                adContext.receptor.rigid_pdbqt = rigid_receptor
                adContext.receptor.flex_pdbqt = flex_receptor

                # self.logger.debug(f'{output}')
                # for chain, contents in chains.items():
                #     for res in contents:
                #         form.flexRes_lstw.addItem(f'{chain} : {str(res.resn)}{str(res.resi)}')

                self.logger.info(f'Success generating flexible receptor with flexible residues {res_string}')
                print(f'Success generating flexible receptor with flexible residues {res_string}')
            else:
                self.logger.error(
                    f'Generating receptor {adContext.receptor.name} with flexible residues {res_string} failed!')

        # form.flexRes_lstw.addItems(stored.flexible_residues)

