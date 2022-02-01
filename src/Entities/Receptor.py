import os

"""
    attributes:
        selection
        name - should act as an unique identifier (ID)
        pdbqt_location - the path to the generated/to be generated pdbqt file of the receptor
        flexible_residues - a list (dictionary) of the flexible residues of the receptor
"""


class Receptor:

    def __init__(self, onReceptorAdded=None) -> None:
        self.selection = None
        self.name = None
        self.pdbqt_location = None
        self.rigid_pdbqt = None
        self.flex_pdbqt = None

        self.flexible_path = None
        self.flexible_residues = {}
        self.fromPymol = True

        self.onReceptorAdded = onReceptorAdded

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
                # full_res_name = pid + ':' + chain + ':' + '_'.join(ress)
                res_string = f'{str(res.resn) + res.resi}'
                ress.append(res_string)
            # TODO: review this, flex_receptor doesn't accept it
            full_res_string = '_'.join(ress)
            chain_string = chain_string + full_res_string

            chains.append(chain_string)

        final_str = ','.join(chains)

        # logging.info(final_str)
        # NOTE: should return final_string
        return full_res_string

    def __repr__(self):
        pdbqt_location = 'No PDBQT' if self.pdbqt_location is None else self.pdbqt_location
        rigid_pdbqt = 'No rigidPDBQT' if self.rigid_pdbqt is None else self.rigid_pdbqt
        flex_pdbqt = 'No flexPDBQT' if self.flex_pdbqt is None else self.flex_pdbqt
        return f'Receptor(name={self.name}, pdbqt={pdbqt_location}, rigid={rigid_pdbqt}, flex={flex_pdbqt})'