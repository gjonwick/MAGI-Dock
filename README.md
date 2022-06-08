# MAGI-Dock
Docking plugin for PyMol

Molecular docking simulation of small molecule drugs to macromolecules is a valuable tool in structural biology and medicinal chemistry research, also thanks to many available free resources. Like many open-source programs in the field, free docking softwares rely on a command-line interface, and steps that require interaction with molecular structures by making use of external graphics software, which are often limited in number and very specific. In addition, such features usually need a re-training of the staff, which may hamper the usage, especially in a company environment. MAGI-Dock is a graphical user interface that brings together the power of Autodock Vina and PyMOL. It comes as a free PyMOL plugin that assists the user along the docking workflow, focusing on docking box set-up.



# INSTALLATION

In order to use this plugin, AutoDock scripts and Vina should be present in the system. For example, MGLTools comes 
with a set of AutoDock scripts that are used to work with receptors and ligands. It is highly recommended to install MGLTools, since it also contains the correct python version and environment to run the scripts. Just using the scripts is not guaranteed to work, since they rely in a lot of libraries that come with MGLTools installation.

The plugin is designed to work in two types of environments.

1. In the case environment modules are present (this is usually the case when working with remote servers), the corresponding mgltools and vina modules should be loaded prior to running pymol, on the same shell (e.g. module load mgltools/1.5.7). There is no need to specify paths in the config section of the plugin, other than the working path and box path.

2. In the case of personal computers (which I guess would be the most popular option), the users have to make sure MGLTools is installed in their system and there is a vina executable somewhere in the system (the vina executable should be named vina.exe). The AutodockTools and vina executable folder path should be specified in the config tab of the plugin before starting the docking steps.


A vina executable can be found here: https://github.com/ccsb-scripps/AutoDock-Vina/releases (note: the plugin expects v1.2 releases)