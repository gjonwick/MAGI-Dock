""" Python binding with AutoDock. """

import os

class AutoDockComand():

    def __init__(self):
        pass

class AutoDock:

    command_list = ['prepare_receptor', 'prepare_ligand', 'prepare_flex']

    def __init__(self):
        pass

def load_ad_commands():
    return {}


globals().update(load_ad_commands())
