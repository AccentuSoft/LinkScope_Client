#!/usr/bin/env python3

import os
import shutil
from os import listdir
import site
import sys
import venv
import subprocess
import importlib.util
import contextlib
import yaml
from pathlib import Path

from PySide6 import QtWidgets, QtCore


class ModulesManager:

    def __init__(self, mainWindow):
        self.mainWindow = mainWindow
        self.baseAppStoragePath = Path(
            QtCore.QStandardPaths.standardLocations(
                QtCore.QStandardPaths.StandardLocation.AppDataLocation)[0])
        self.baseAppStoragePath.mkdir(exist_ok=True, parents=True)
        self.modulesBaseDirectoryPath = self.baseAppStoragePath / "User Modules Storage"
        self.modulesBaseDirectoryPath.mkdir(exist_ok=True)
        self.modulesDirectoryPath = self.modulesBaseDirectoryPath / "Modules"
        self.modulesDirectoryPath.mkdir(exist_ok=True)
        self.modulesPythonPath = self.modulesBaseDirectoryPath / 'bin' / 'python3'
        self.modules = {}

        venvThread = InitialiseVenvThread(self)
        venvThread.configureVenvOfMainThreadSignal.connect(self.configureVenv)
        venvThread.start()

    def configureVenv(self, venvPath):
        binDir = os.path.dirname(venvPath / 'bin')
        base = binDir[: -len("bin") - 1]  # strip away the bin part from the __file__, plus the path separator

        # prepend bin to PATH (this file is inside the bin directory)
        os.environ["PATH"] = os.pathsep.join([binDir] + os.environ.get("PATH", "").split(os.pathsep))
        os.environ["VIRTUAL_ENV"] = base  # virtual env is right above bin directory

        # add the virtual environments libraries to the host python import mechanism
        prevLength = len(sys.path)
        packagesPath = str(list((venvPath / 'lib').glob('python*'))[0] / 'site-packages')

        for lib in packagesPath.split(os.pathsep):
            path = os.path.realpath(os.path.join(binDir, lib))
            site.addsitedir(path)
        sys.path[:] = sys.path[prevLength:] + sys.path[0:prevLength]

        sys.real_prefix = sys.prefix
        sys.prefix = base

    def installModule(self, uniqueModuleName: str, moduleFilePath: Path) -> bool:
        newModuleDirectoryPath = self.modulesDirectoryPath / uniqueModuleName
        if newModuleDirectoryPath.exists():
            self.mainWindow.MESSAGEHANDLER.error(f'Could not install Module {uniqueModuleName}: Module already exists.')
            return False
        shutil.copytree(moduleFilePath, newModuleDirectoryPath)

        moduleRequirements = newModuleDirectoryPath / "requirements.txt"
        moduleAssetsPath = newModuleDirectoryPath / "assets"
        resolutionsPath = newModuleDirectoryPath / "Resolutions"
        entitiesPath = newModuleDirectoryPath / "Entities"
        moduleAssetsPath.mkdir(exist_ok=True)
        resolutionsPath.mkdir(exist_ok=True)
        entitiesPath.mkdir(exist_ok=True)

        moduleDetailsPath = newModuleDirectoryPath / "module.yml"
        if not moduleDetailsPath.exists():
            moduleDetailsPath = newModuleDirectoryPath / "module.yaml"
            if not moduleDetailsPath.exists():
                self.mainWindow.MESSAGEHANDLER.error(f'Could not install Module {uniqueModuleName}: '
                                                     f'module.yml not found.')
            shutil.rmtree(newModuleDirectoryPath)
            return False

        with open(moduleDetailsPath, 'r') as yamlFile:
            try:
                moduleDetails = yaml.safe_load(yamlFile)
            except yaml.YAMLError as yExc:
                self.mainWindow.MESSAGEHANDLER.error(f'Could not install Module {uniqueModuleName}. '
                                                     f'Exception while loading module: {yExc}')
                shutil.rmtree(newModuleDirectoryPath)
                return False
        try:
            author = moduleDetails['Author']
            version = moduleDetails['Version']
            moduleName = moduleDetails['Module Name']
            notes = moduleDetails['Notes']
        except Exception as exc:
            self.mainWindow.MESSAGEHANDLER.error(f'Could not install Module {uniqueModuleName}. '
                                                 f'Exception while loading module details: {exc}')
            shutil.rmtree(newModuleDirectoryPath)
            return False

        if moduleRequirements.exists():
            cmdStr = f"'{self.modulesPythonPath}' -m pip install -r '{moduleRequirements}'"
            subprocess.run(cmdStr, shell=True)

        self.mainWindow.MESSAGEHANDLER.info(f'Loaded module {moduleName} version {version} by {author}.')
        self.mainWindow.MESSAGEHANDLER.debug(f'Module {moduleName} notes: {notes}')
        return True

    def loadModule(self, uniqueModuleName: str) -> bool:
        newModuleDirectoryPath = self.modulesDirectoryPath / uniqueModuleName
        moduleDetailsPath = newModuleDirectoryPath / "module.yml"
        if not moduleDetailsPath.exists():
            moduleDetailsPath = newModuleDirectoryPath / "module.yaml"
            if not moduleDetailsPath.exists():
                self.mainWindow.MESSAGEHANDLER.error(f'Could not load Module {uniqueModuleName}: '
                                                     f'module.yml not found.')
            return False

        with open(moduleDetailsPath, 'r') as yamlFile:
            try:
                moduleDetails = yaml.safe_load(yamlFile)
            except yaml.YAMLError as yExc:
                self.mainWindow.MESSAGEHANDLER.error(f'Could not load Module {uniqueModuleName}. '
                                                     f'Exception while loading module: {yExc}')
                return False
        try:
            author = moduleDetails['Author']
            version = moduleDetails['Version']
            moduleName = moduleDetails['Module Name']
            notes = moduleDetails['Notes']
        except Exception as exc:
            self.mainWindow.MESSAGEHANDLER.error(f'Could not load Module {uniqueModuleName}. '
                                                 f'Exception while loading module details: {exc}')
            return False

        moduleEntities = self.mainWindow.RESOURCEHANDLER.loadModuleEntities(
            newModuleDirectoryPath / "Entities")
        moduleResolutions = self.mainWindow.RESOLUTIONMANAGER.loadResolutionsFromDir(
            newModuleDirectoryPath / "Resolutions")
        self.modules[uniqueModuleName] = {'author': author, 'version': version, 'name': moduleName, 'notes': notes,
                                          'entities': moduleEntities, 'resolutions': moduleResolutions}
        self.mainWindow.MESSAGEHANDLER.info(f'Loaded Module: {moduleName}')
        return True

    def loadAllModules(self) -> bool:
        moduleLoadFailuresCount = 0
        for uniqueModuleName in listdir(self.modulesDirectoryPath):
            if not self.loadModule(uniqueModuleName):
                moduleLoadFailuresCount += 1
                if moduleLoadFailuresCount > 2:
                    self.mainWindow.MESSAGEHANDLER.critical(
                        f'Failed loading too many Modules, aborting Module loading.',
                        exc_info=False)
                    return False
            self.mainWindow.MESSAGEHANDLER.info(f'Loaded module: {uniqueModuleName}')
        return True

    def uninstallModule(self, uniqueModuleName: str) -> bool:
        newModuleDirectoryPath = self.modulesDirectoryPath / uniqueModuleName
        if not newModuleDirectoryPath.exists():
            self.mainWindow.MESSAGEHANDLER.error(f'Could not uninstall Module {uniqueModuleName}: '
                                                 f'Module does not exist.')
            self.modules.pop(uniqueModuleName)
            return False
        try:
            shutil.rmtree(newModuleDirectoryPath)
        except Exception as exc:
            self.mainWindow.MESSAGEHANDLER.error(f'Could not uninstall Module {uniqueModuleName}: '
                                                 f'Error occurred: {exc}.')
            return False

        # No need to uninstall anything from venv - more likely to cause issues than fix anything.
        self.modules.pop(uniqueModuleName)
        return True


class ModulePacksListViewer(QtWidgets.QDialog):

    def __init__(self, parent: ModulesManager):
        super().__init__()
        self.modulesManager = parent

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        self.setWindowTitle('Installed Modules List')

        installedModulesLabel = QtWidgets.QLabel("Installed Modules")
        layout.addWidget(installedModulesLabel)

        self.modulePackList = QtWidgets.QListWidget()
        addModulePackButton = QtWidgets.QPushButton('+')
        removeModulePackButton = QtWidgets.QPushButton('-')

        closeButton = QtWidgets.QPushButton('Close')
        closeButton.clicked.connect(self.accept)

    def removeModulePack(self) -> bool:
        itemsToRemove = self.modulePackList.selectedItems()
        if len(itemsToRemove) < 1:
            self.modulesManager.mainWindow.MESSAGEHANDLER.warning('No items selected, nothing to remove.', popUp=True)
            return True
        for item in itemsToRemove:
            pass

    def addModulePack(self) -> bool:
        if addModuleDialog := AddModuleDialog().exec():
            print('RET', addModuleDialog)
            # TODO
            return True
        return False


class ModuleDetailsViewer(QtWidgets.QDialog):

    def __init__(self, moduleDetails: dict):
        super().__init__()
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        self.setWindowTitle(f'Details for Module: {moduleDetails["name"]}')
        authorLabel = QtWidgets.QLabel('Author:')
        authorText = QtWidgets.QLineEdit(moduleDetails['author'])
        authorText.setReadOnly(True)
        versionLabel = QtWidgets.QLabel('Version:')
        versionText = QtWidgets.QLineEdit(moduleDetails['version'])
        versionText.setReadOnly(True)
        nameLabel = QtWidgets.QLabel('Notes:')
        nameText = QtWidgets.QTextEdit(moduleDetails['notes'])
        nameText.setReadOnly(True)
        entitiesLabel = QtWidgets.QLabel('Entities:')
        resolutionsLabel = QtWidgets.QLabel('Resolutions:')


class AddModuleDialog(QtWidgets.QDialog):

    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        self.setWindowTitle('Add Module')
        self.moduleToAddPath = QtWidgets.QLineEdit()
        instructionText = QtWidgets.QLabel('Enter the path to the folder containing the module to install, or '
                                           'the URL to a git repository where the module is stored.')
        instructionText.setWordWrap(True)
        instructionText.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.moduleToAddPath.setPlaceholderText('Path to new Module')
        self.moduleToAddPath.setToolTip('Either paste a URL from a site like Github, or a path to a local folder.')
        selectLocalFolderButton = QtWidgets.QPushButton('Select Local Folder')
        selectLocalFolderButton.clicked.connect(self.selectLocalFolder)
        acceptButton = QtWidgets.QPushButton('Confirm')
        acceptButton.clicked.connect(self.accept)
        rejectButton = QtWidgets.QPushButton('Cancel')
        rejectButton.clicked.connect(self.reject)

    def selectLocalFolder(self) -> None:
        moduleFolderDialog = QtWidgets.QFileDialog()
        moduleFolderDialog.setOption(QtWidgets.QFileDialog.Option.DontUseNativeDialog, True)
        moduleFolderDialog.setViewMode(QtWidgets.QFileDialog.ViewMode.List)
        moduleFolderDialog.setFileMode(QtWidgets.QFileDialog.FileMode.Directory)
        moduleFolderDialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptOpen)
        moduleFolderDialog.setDirectory(str(Path.home()))

        if moduleFolderDialog.exec():
            folderPath = Path(moduleFolderDialog.selectedFiles()[0])
            self.moduleToAddPath.setText(str(folderPath))

    def accept(self) -> None:
        moduleLoc = self.moduleToAddPath.text()
        pass  # TODO - Check for validity
        if moduleLoc:  # Check if URL
            pass
        else:
            moduleLocPath = Path(moduleLoc)
        super().accept()


class InitialiseVenvThread(QtCore.QThread):
    configureVenvOfMainThreadSignal = QtCore.Signal(Path)

    def __init__(self, modulesManager: ModulesManager):
        super().__init__()
        self.modulesManager = modulesManager

    def run(self) -> None:
        venvPath = self.modulesManager.modulesBaseDirectoryPath
        if not (venvPath / 'bin').exists():
            venv.create(venvPath, symlinks=True, with_pip=True, upgrade_deps=True)

        self.modulesManager.configureVenv(venvPath)
        self.configureVenvOfMainThreadSignal.emit(venvPath)

        # Install / upgrade playwright if not already installed, since it needs special treatment.
        cmdStr = f"'{self.modulesManager.modulesPythonPath}' -m pip install --upgrade playwright && " \
                 f"'{self.modulesManager.modulesPythonPath}' -m playwright install"
        subprocess.run(cmdStr, shell=True)
