# MAGI-Dock
Docking plugin for PyMol

Molecular docking simulation of small molecule drugs to macromolecules is a valuable tool in structural biology and medicinal chemistry research, also thanks to many available free resources. Like many open-source programs in the field, free docking softwares rely on a command-line interface, and steps that require interaction with molecular structures by making use of external graphics software, which are often limited in number and very specific. In addition, such features usually need a re-training of the staff, which may hamper the usage, especially in a company environment. MAGI-Dock is a graphical user interface that brings together the power of Autodock Vina and PyMOL. It comes as a free PyMOL plugin that assists the user along the docking workflow, focusing on docking box set-up.



# INSTALLATION

In order to use this plugin, AutoDock scripts and Vina should be present in the system. For example, MGLTools comes 
with a set of AutoDock scripts that are used to work with receptors and ligands. It is highly recommended to install MGLTools, since it also contains the correct python version and environment to run the scripts. Just using the scripts is not guaranteed to work, since they rely in a lot of libraries that come with MGLTools installation.

The plugin is designed to work in two types of environments.

1. In the case environment modules are present (this is usually the case when working with remote servers), the corresponding mgltools and vina modules should be loaded prior to running pymol, on the same shell (e.g. module load mgltools/1.5.7). There is no need to specify paths in the config section of the plugin, other than the working path and box path.

2. In the case of personal computers (which I guess would be the most popular option), the users have to make sure MGLTools is installed in their system and there is a vina executable somewhere in the system (the vina executable should be named vina.exe). The AutodockTools and vina executable folder path should be specified in the config tab of the plugin before starting the docking steps.

3. If users shall use Autodock scoring function to run docking, Autodock4 and Autogrid executables should be installed. Autodock 4 can be found here: https://autodock.scripps.edu, and after the installation the executables can be found in: *C:\Program Files (x86)*\The Scripps Research Institute\Autodock\4.2.6



## CONFIGURATION
In the Config tab there are six options for the users to configure.
  - MGL python exe: should specify the path to the python executable that comes with the installation of MGL tools. e.g. /Program Files (x86)/MGLTools-1.5.7/python.exe. (MGLTools-1.5.7 will be used as the default in this tutorial.)
  - AutoDock Tools Folder: should specify the path to the autodock scripts, located in */MGLTools-1.5.7/Lib/site-packages/AutoDockTools/Utilities24
  - Vina Executable: should specify the path to the vina executable. A vina executable can be found here: https://github.com/ccsb-scripps/AutoDock-Vina/releases (note: the plugin expects v1.2 releases).
  - Working Dir: should specify the directory (folder) where the working files will be generated, including receptor and ligand files, as well as results.
  - Box Path: should specify the config file that will be used by Vina, and contains the docking box coordinates. It is recommended to keep only the coordinates in this file, since other running parameters can be specified in the plugin interface by the user.

If Vina scoring function will be used, this options are enough to run docking; otherwise, if Autodock4 will be used as the scoring function, the following option must be specified:  
  - Autogird Executable: should specify the path to autodock4 and autogrid executables. 


## Installing the plugin
Download the repo and extract the files. Then, in PyMOL click on Plugin -> Plugin Manager -> Install New Plugin -> Install from local file (Choose File ...) and select the __init__.py file in the plugin folder. You can access the plugin from the Plugin tab in PyMOL.


## Minor Bugs

Trying to generate a box without specifying the working directory will cause the box to not be saved even after selecting a working dir. However, by temporary moving the box, the path will be generated automatically.

Sometimes, the load prepared_receptor option in the Docking Tab is not able to read the .pdbqt file.
