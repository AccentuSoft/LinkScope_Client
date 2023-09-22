#!/usr/bin/env python3

import contextlib
import os
import shutil
import site
import sys
import venv
import subprocess
import yaml
import pygit2
from pathlib import Path
from enum import Enum
from urllib.parse import urlparse
from uuid import uuid4
from base64 import b64decode
from threading import Lock

from PySide6 import QtWidgets, QtCore, QtSvg, QtGui


class ModulesManager:

    def __init__(self, mainWindow):
        self.mainWindow = mainWindow
        self.baseAppStoragePath = Path(
            QtCore.QStandardPaths.standardLocations(
                QtCore.QStandardPaths.StandardLocation.AppDataLocation)[0])
        self.baseAppStoragePath.mkdir(exist_ok=True, parents=True)
        self.modulesBaseDirectoryPath = self.baseAppStoragePath / "User Module Packs Storage"
        self.modulesBaseDirectoryPath.mkdir(exist_ok=True)
        self.browsersBaseDirectoryPath = self.baseAppStoragePath / "Browsers"
        self.browsersBaseDirectoryPath.mkdir(exist_ok=True)
        self.modulesRequirementsPath = self.modulesBaseDirectoryPath / "requirements.txt"
        self.modulesRequirementsPath.touch(mode=0o700, exist_ok=True)
        self.modulesRequirementsTempPath = self.modulesBaseDirectoryPath / "requirements.txt.tmp"
        self.modulesPythonPath = self.modulesBaseDirectoryPath / 'bin' / 'python3'
        self.upgradeThread = None
        self.moduleReqsThread = None
        self.uninstallThread = None
        self.modulePacksListViewer = None
        self.upgradeLock = Lock()
        self.sources = self.mainWindow.SETTINGS.value("Program/Sources/Sources List")
        self.modulePacks = self.mainWindow.SETTINGS.value("Program/Sources/Module Packs List")
        self.loadedModules = {}

        self.venvThread = InitialiseVenvThread(self)
        self.venvThread.configureVenvOfMainThreadSignal.connect(self.configureVenv)
        self.venvThread.start()

    def afterUpgrade(self, upgradeStatus: bool):
        self.mainWindow.MESSAGEHANDLER.info(f"Upgrade status: {'Success' if upgradeStatus else 'Failed'}")
        self.mainWindow.setStatus('Environment Updated.')

    def save(self) -> bool:
        self.mainWindow.SETTINGS.setValue("Program/Sources/Sources List", self.sources)
        self.mainWindow.SETTINGS.setValue("Program/Sources/Module Packs List", self.modulePacks)
        return True

    def loadYamlFile(self, filePath: Path):
        with open(filePath, 'r') as yamlFile:
            try:
                fileContents = yaml.safe_load(yamlFile)
            except yaml.YAMLError:
                self.mainWindow.MESSAGEHANDLER.error(f'Exception while processing YAML file: {filePath}.')
                return None
        # Never return None if no errors occurred -> gets around None returned on empty file.
        # {} == False
        return fileContents if fileContents is not None else {}

    def configureVenv(self, venvPath):
        binDir = os.path.dirname(venvPath / 'bin')
        base = binDir[: -len("bin") - 1]  # strip away the bin part from the __file__, plus the path separator

        # prepend bin to PATH (this file is inside the bin directory)
        os.environ["PATH"] = os.pathsep.join([binDir] + os.environ.get("PATH", "").split(os.pathsep))
        os.environ["VIRTUAL_ENV"] = base  # virtual env is right above bin directory
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(self.browsersBaseDirectoryPath)

        # add the virtual environments libraries to the host python import mechanism
        prevLength = len(sys.path)
        packagesPath = str(list((venvPath / 'lib').glob('python*'))[0] / 'site-packages')

        for lib in packagesPath.split(os.pathsep):
            path = os.path.realpath(os.path.join(binDir, lib))
            site.addsitedir(path)
        sys.path[:] = sys.path[prevLength:] + sys.path[:prevLength]

        sys.real_prefix = sys.prefix
        sys.prefix = base

        self.loadAllModules()

        self.mainWindow.MESSAGEHANDLER.info("Configured Modules environment and loaded Modules.")
        self.mainWindow.MESSAGEHANDLER.debug(f"OS Path: {os.environ['PATH']}")

        self.upgradeThread = UpgradeVenvThread(self, useTempFile=False, fullUpgrade=True)
        self.upgradeThread.upgradeVenvThreadSignal.connect(self.afterUpgrade)
        self.upgradeThread.start()

    def loadModule(self, modulePath: Path) -> bool:
        moduleDetailsPath = modulePath / "module.yml"
        if not moduleDetailsPath.exists():
            moduleDetailsPath = modulePath / "module.yaml"
            if not moduleDetailsPath.exists():
                self.mainWindow.MESSAGEHANDLER.error(f'Could not load Module {modulePath.name}: '
                                                     f'module.yml not found.')
            return False

        if not (moduleDetails := self.loadYamlFile(moduleDetailsPath)):
            return False

        try:
            author = moduleDetails['author']
            version = moduleDetails['version']
            moduleName = modulePath.name
            description = moduleDetails['description']
        except Exception as exc:
            self.mainWindow.MESSAGEHANDLER.error(f'Could not load Module {modulePath.name}. '
                                                 f'Exception while loading module details: {exc}')
            return False

        self.mainWindow.RESOURCEHANDLER.loadModuleAssets(modulePath)
        moduleEntities = self.mainWindow.RESOURCEHANDLER.loadModuleEntities(modulePath)
        moduleResolutions = self.mainWindow.RESOLUTIONMANAGER.loadResolutionsFromDir(
            modulePath / "Resolutions")
        self.loadedModules[f"{modulePath.parent.name} | {moduleName}"] = \
            {'author': author, 'version': version, 'name': moduleName, 'description': description,
             'entities': moduleEntities, 'resolutions': moduleResolutions}
        self.mainWindow.MESSAGEHANDLER.info(f'Loaded Module: {moduleName}')
        return True

    def loadAllModules(self) -> bool:
        moduleLoadFailuresCount = 0
        for sourceDict in self.sources.values():
            sourceUUID = sourceDict['UUID']
            for modulePackDetails in self.modulePacks[sourceUUID].values():
                if modulePackDetails['Installed']:
                    for module in modulePackDetails['modules']:
                        modulePath = self.modulesBaseDirectoryPath / sourceUUID / module
                        if not self.loadModule(modulePath):
                            moduleLoadFailuresCount += 1
                            if moduleLoadFailuresCount > 2:
                                self.mainWindow.MESSAGEHANDLER.critical(
                                    'Failed loading too many Modules, aborting Module loading.',
                                    exc_info=False,
                                )
                                return False
        return True

    def showSourcesManager(self):
        SourcesManager(self).exec()

    def installSource(self, newSourceDict: dict) -> bool:
        newSourceURI = newSourceDict['URI']

        authType = AuthType.NONE
        authCreds = None
        schemaType = SchemaType.LOCAL
        if isRemote := newSourceDict['Remote']:
            authDetails = newSourceDict['Auth']
            parsedURL = urlparse(newSourceURI)
            if authDetails is not None:
                username = authDetails[0]
                passAuth = authDetails[1]
                authType = AuthType.KEY if isinstance(authDetails[1], Path) else AuthType.PASSWORD
                authCreds = (username, passAuth)

            # Scheme does not matter for now because we always assume that we are pointed to a repository.
            #   This might change in the future. 10/05/2023
            if parsedURL.scheme in ['https', 'http']:
                schemaType = schemaType.HTTPS
            elif parsedURL.scheme == 'ssh':
                schemaType = schemaType.SSH
            elif parsedURL.scheme == 'git':
                schemaType = schemaType.GIT
            else:
                self.mainWindow.MESSAGEHANDLER.error(f'Cannot add source: {newSourceURI}\n\n'
                                                     f'Reason: Unsupported Schema type: {parsedURL.scheme}.',
                                                     popUp=True,
                                                     exc_info=False)
                return False
        elif newSourceURI.lower().startswith('file://'):
            newSourceURI = newSourceURI[7:]

        if newSourceURI in self.sources:
            self.mainWindow.MESSAGEHANDLER.error(f'Cannot add source: {newSourceURI}\n\n'
                                                 f'Reason: Source already exists.',
                                                 popUp=True,
                                                 exc_info=False)
            return False

        self.sources[newSourceURI] = {'URI': newSourceURI, 'Remote': isRemote, 'AuthType': authType,
                                      'AuthCreds': authCreds, 'SchemaType': schemaType, 'UUID': str(uuid4())}
        if self.syncSource(newSourceURI):
            self.save()
        else:
            self.sources.pop(newSourceURI)
            return False

        return True

    def uninstallSource(self, sourceURI: str) -> bool:
        source = self.sources.pop(sourceURI)
        with contextlib.suppress(FileNotFoundError):
            shutil.rmtree(self.modulesBaseDirectoryPath / source['UUID'])
        self.modulePacks.pop(source['UUID'])
        self.save()
        return True

    def syncSource(self, sourceURI: str, onlySyncExisting: bool = False, showMessages: bool = True) -> bool:
        source = self.sources[sourceURI]
        sourceUUID = source['UUID']
        destinationPath = self.modulesBaseDirectoryPath / sourceUUID

        if source['Remote']:
            try:
                if authType := source['AuthType']:
                    authCreds = source['AuthCreds']
                    if authType == AuthType.PASSWORD:
                        callbacks = pygit2.RemoteCallbacks(credentials=pygit2.UserPass(username=authCreds[0],
                                                                                       password=authCreds[1]))
                    else:
                        callbacks = pygit2.RemoteCallbacks(credentials=pygit2.Keypair(username=authCreds[0],
                                                                                      privkey=authCreds[1],
                                                                                      pubkey=authCreds[2],
                                                                                      passphrase=""))
                    pygit2.clone_repository(source['URI'], destinationPath, callbacks=callbacks)
                else:
                    pygit2.clone_repository(source['URI'], destinationPath)
            except pygit2.GitError as gitErr:
                if showMessages:
                    self.mainWindow.MESSAGEHANDLER.error(f'Could not sync source {sourceURI}: {gitErr}',
                                                         popUp=True, exc_info=True)
                return False
        else:
            try:
                shutil.copytree(Path(sourceURI), destinationPath, dirs_exist_ok=True)
                self.mainWindow.MESSAGEHANDLER.info('Copied source files.')
            except FileNotFoundError:
                if showMessages:
                    self.mainWindow.MESSAGEHANDLER.error(f'Could not sync source {sourceURI}: Source folder not found.',
                                                         popUp=True, exc_info=False)
                return False

        if not (modulePackFiles := [file for file in os.listdir(destinationPath) if file.endswith(('.yml', '.yaml'))]):
            if showMessages:
                self.mainWindow.MESSAGEHANDLER.error(f'No Module Pack files found for source: {sourceURI}.',
                                                     popUp=True,
                                                     exc_info=False)
            return False

        if not onlySyncExisting:
            if sourceUUID not in self.modulePacks:
                self.modulePacks[sourceUUID] = {}

            for modulePack in modulePackFiles:
                modulePackPath = destinationPath / modulePack
                if not (packDetails := self.loadYamlFile(modulePackPath)):
                    continue
                packDetails['Source UUID'] = sourceUUID
                packDetails['UUID'] = str(uuid4())
                packDetails['Installed'] = False
                self.modulePacks[sourceUUID][packDetails['UUID']] = packDetails

        return True

    def showModuleManager(self):
        self.modulePacksListViewer = ModulePacksListViewer(self)
        self.modulePacksListViewer.exec()
        self.modulePacksListViewer = None

    def installModulePackInit(self, sourceUUID: str, modulePackUUID: str) -> None:
        self.upgradeLock.acquire()
        packDetails = self.modulePacks[sourceUUID][modulePackUUID]

        self.moduleReqsThread = InstallRequirementsThread(self, sourceUUID, modulePackUUID)

        progress = QtWidgets.QProgressDialog(f'Installing Module: {packDetails["label"]}...',
                                             '', 0, 3, self.mainWindow)

        # Remove Cancel button from progress bar (user should not be able to stop canvas from loading).
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)
        progress.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.moduleReqsThread.progressSignal.connect(progress.setValue)
        self.moduleReqsThread.installFinishedSignal.connect(self.installModulePackFin)
        self.moduleReqsThread.start()

    def installModulePackFin(self, success: bool, modulePackLabel: str, sourceUID: str, modulePackUID: str):
        self.upgradeLock.release()
        if success:
            self.mainWindow.MESSAGEHANDLER.info(f'Module Pack successfully installed: {modulePackLabel}')
            with contextlib.suppress(AttributeError):
                self.modulePacksListViewer.setInstallCompletedForModulePackWidget()
            modulePackDetails = self.modulePacks[sourceUID][modulePackUID]
            for module in modulePackDetails['modules']:
                modulePath = self.modulesBaseDirectoryPath / sourceUID / module
                if not self.loadModule(modulePath):
                    self.mainWindow.MESSAGEHANDLER.warning(
                        f'Failed loading module: {modulePackLabel}.',
                        exc_info=False,
                    )
            self.mainWindow.reloadModules(onlyUpdateDockbar=True)
        else:
            self.mainWindow.MESSAGEHANDLER.info(f'Module Pack installation failed: {modulePackLabel}')

    def removeModulePack(self, modulePackDict: dict) -> None:
        self.upgradeLock.acquire()

        self.uninstallThread = UninstallModuleThread(self, modulePackDict)

        progress = QtWidgets.QProgressDialog(f'Uninstalling Module: {modulePackDict["label"]}...',
                                             '', 0, 3, self.mainWindow)

        # Remove Cancel button from progress bar (user should not be able to stop canvas from loading).
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)
        progress.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.uninstallThread.progressSignal.connect(progress.setValue)
        self.uninstallThread.uninstallFinishedSignal.connect(self.uninstallModulePackFin)
        self.uninstallThread.start()

    def uninstallModulePackFin(self, success: bool, modulePackLabel: str):
        self.upgradeLock.release()
        if success:
            self.mainWindow.MESSAGEHANDLER.info(f'Module Pack successfully uninstalled: {modulePackLabel}')
            with contextlib.suppress(AttributeError):
                self.modulePacksListViewer.setUninstallCompletedForModulePackWidget()
        else:
            self.mainWindow.MESSAGEHANDLER.info(f'Module Pack uninstallation failed: {modulePackLabel}')


class SourcesManager(QtWidgets.QDialog):

    def __init__(self, modulesManager: ModulesManager):
        super().__init__()
        self.modulesManager = modulesManager
        self.setWindowTitle('Sources Manager')

        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)

        sourcesListLabel = QtWidgets.QLabel('Installed Sources')
        sourcesListLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.sourcesList = QtWidgets.QListWidget()
        self.sourcesList.setLayoutMode(self.sourcesList.LayoutMode.SinglePass)
        self.sourcesList.setSelectionMode(self.sourcesList.SelectionMode.SingleSelection)
        for source in self.modulesManager.sources:
            self.sourcesList.addItem(source)

        addSourceButton = QtWidgets.QPushButton('Add New Source')
        addSourceButton.clicked.connect(self.addSource)
        removeSourceButton = QtWidgets.QPushButton('Remove Selected Source')
        removeSourceButton.clicked.connect(self.removeSource)

        layout.addWidget(sourcesListLabel, 0, 0, 1, 2)
        layout.addWidget(self.sourcesList, 1, 0, 3, 2)
        layout.addWidget(addSourceButton, 4, 1, 1, 1)
        layout.addWidget(removeSourceButton, 4, 0, 1, 1)

    def addSource(self) -> bool:
        addSourceDialog = AddSourceDialog()
        if addSourceDialog.exec():
            newSource = addSourceDialog.sourceDict
            newSourceURI = newSource['URI']
            if self.modulesManager.installSource(newSource):
                self.sourcesList.addItem(newSourceURI)
                return True
            return False

    def removeSource(self) -> bool:
        with contextlib.suppress(IndexError):
            selectedItem = self.sourcesList.selectedItems()[0]
            if self.modulesManager.uninstallSource(selectedItem.text()):
                self.sourcesList.takeItem(self.sourcesList.row(selectedItem))
                return True
            return False


class AddSourceDialog(QtWidgets.QDialog):

    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)
        self.setWindowTitle('Add New Source')

        addSourceLabel = QtWidgets.QLabel('Fill in the fields to add a new source.\n'
                                          'Sources must either be a folder on the local system, or a remote Git '
                                          'repository, accessible via the HTTP, SSH or GIT transports.\n'
                                          'Local URI Example:\n/home/user/source_folder\n'
                                          'Remote URI Example:\ngit://github.com/example/example.git')
        addSourceLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        addSourceLabel.setWordWrap(True)
        localOrRemoteSource = QtWidgets.QWidget()
        localOrRemoteSourceLayout = QtWidgets.QVBoxLayout()
        localOrRemoteSource.setLayout(localOrRemoteSourceLayout)
        self.localSourceRadioButton = QtWidgets.QRadioButton('Local Source', localOrRemoteSource)
        self.remoteSourceRadioButton = QtWidgets.QRadioButton('Remote Source', localOrRemoteSource)
        self.remoteSourceRadioButton.setChecked(True)
        self.remoteSourceRadioButton.toggled.connect(self.toggleLocalOrRemote)
        localOrRemoteSourceLayout.addWidget(self.localSourceRadioButton)
        localOrRemoteSourceLayout.addWidget(self.remoteSourceRadioButton)

        localOrRemoteInput = QtWidgets.QWidget()
        self.localOrRemoteInputLayout = QtWidgets.QStackedLayout()
        localOrRemoteInput.setLayout(self.localOrRemoteInputLayout)

        remoteInputContainerWidget = QtWidgets.QWidget()
        remoteInputContainerWidgetLayout = QtWidgets.QGridLayout()
        remoteInputContainerWidget.setLayout(remoteInputContainerWidgetLayout)
        remoteInputLabel = QtWidgets.QLabel('Enter the URI of the new source:')
        remoteInputLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        remoteInputContainerWidgetLayout.addWidget(remoteInputLabel, 0, 0)
        self.remoteSourceInput = QtWidgets.QLineEdit()
        remoteInputContainerWidgetLayout.addWidget(self.remoteSourceInput, 1, 0)

        self.localOrRemoteInputLayout.addWidget(remoteInputContainerWidget)

        localInputContainerWidget = QtWidgets.QWidget()
        localInputContainerWidgetLayout = QtWidgets.QGridLayout()
        localInputContainerWidget.setLayout(localInputContainerWidgetLayout)
        localInputLabel = QtWidgets.QLabel('Enter the path to the new source:')
        localInputLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        localInputContainerWidgetLayout.addWidget(localInputLabel, 0, 0, 1, 2)
        self.localSourceInput = QtWidgets.QLineEdit()
        self.localSourceInput.setToolTip('Input the local path to the folder containing the module packs.')
        localInputContainerWidgetLayout.addWidget(self.localSourceInput, 1, 0, 1, 1)
        localInputSelectFileButton = QtWidgets.QPushButton('Select Folder')
        localInputSelectFileButton.clicked.connect(self.selectLocalSourceFolder)
        localInputContainerWidgetLayout.addWidget(localInputSelectFileButton, 1, 1, 1, 1)

        self.localOrRemoteInputLayout.addWidget(localInputContainerWidget)

        authenticationLabel = QtWidgets.QLabel('Specify the Authentication needed to access the source:')
        authenticationLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.authenticationOptionWidget = QtWidgets.QWidget()
        authenticationOptionWidgetLayout = QtWidgets.QVBoxLayout()
        self.authenticationOptionWidget.setLayout(authenticationOptionWidgetLayout)
        self.noAuthentication = QtWidgets.QRadioButton('No Authentication', self.authenticationOptionWidget)
        self.noAuthentication.clicked.connect(lambda: self.toggleAuthCreds(0))
        self.usernameAndPassword = QtWidgets.QRadioButton('Username and Password', self.authenticationOptionWidget)
        self.usernameAndPassword.clicked.connect(lambda: self.toggleAuthCreds(1))
        self.usernameAndKey = QtWidgets.QRadioButton('Username and Key File', self.authenticationOptionWidget)
        self.usernameAndKey.clicked.connect(lambda: self.toggleAuthCreds(2))
        self.noAuthentication.setChecked(True)
        authenticationOptionWidgetLayout.addWidget(self.noAuthentication)
        authenticationOptionWidgetLayout.addWidget(self.usernameAndPassword)
        authenticationOptionWidgetLayout.addWidget(self.usernameAndKey)

        self.authenticationCredentialsWidget = QtWidgets.QWidget()
        self.authenticationCredentialsWidgetLayout = QtWidgets.QStackedLayout()
        self.authenticationCredentialsWidget.setLayout(self.authenticationCredentialsWidgetLayout)

        noAuthLabel = QtWidgets.QLabel('No Credentials')
        noAuthLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        usernameAndPasswordWidget = QtWidgets.QWidget()
        usernameAndPasswordWidgetLayout = QtWidgets.QFormLayout()
        usernameAndPasswordWidget.setLayout(usernameAndPasswordWidgetLayout)
        self.usernameInputField = QtWidgets.QLineEdit()
        self.passwordInputField = QtWidgets.QLineEdit()
        usernameAndPasswordWidgetLayout.addRow('Username:', self.usernameInputField)
        usernameAndPasswordWidgetLayout.addRow('Password:', self.passwordInputField)

        usernameAndKeyWidget = QtWidgets.QWidget()
        usernameAndKeyWidgetLayout = QtWidgets.QGridLayout()
        usernameAndKeyWidget.setLayout(usernameAndKeyWidgetLayout)
        privateKeyFileLineWidget = QtWidgets.QWidget()
        privateKeyFileLineWidgetLayout = QtWidgets.QHBoxLayout()
        privateKeyFileLineWidget.setLayout(privateKeyFileLineWidgetLayout)
        publicKeyFileLineWidget = QtWidgets.QWidget()
        publicKeyFileLineWidgetLayout = QtWidgets.QHBoxLayout()
        publicKeyFileLineWidget.setLayout(publicKeyFileLineWidgetLayout)
        self.keyUsernameInputField = QtWidgets.QLineEdit()
        self.privateKeyInputField = QtWidgets.QLineEdit()
        self.publicKeyInputField = QtWidgets.QLineEdit()
        privateKeyInputButton = QtWidgets.QPushButton('Select File')
        privateKeyInputButton.clicked.connect(self.selectLocalPrivateKeyFile)
        publicKeyInputButton = QtWidgets.QPushButton('Select File')
        publicKeyInputButton.clicked.connect(self.selectLocalPublicKeyFile)
        privateKeyFileLineWidgetLayout.addWidget(self.privateKeyInputField)
        privateKeyFileLineWidgetLayout.addWidget(privateKeyInputButton)
        publicKeyFileLineWidgetLayout.addWidget(self.publicKeyInputField)
        publicKeyFileLineWidgetLayout.addWidget(publicKeyInputButton)
        usernameAndKeyWidgetLayout.addWidget(QtWidgets.QLabel('Username:'), 0, 0, 1, 1)
        usernameAndKeyWidgetLayout.addWidget(self.keyUsernameInputField, 0, 1, 1, 1)
        usernameAndKeyWidgetLayout.addWidget(QtWidgets.QLabel('Private Key File:'), 1, 0, 1, 1)
        usernameAndKeyWidgetLayout.addWidget(privateKeyFileLineWidget, 1, 1, 1, 1)
        usernameAndKeyWidgetLayout.addWidget(QtWidgets.QLabel('Public Key File:'), 2, 0, 1, 1)
        usernameAndKeyWidgetLayout.addWidget(publicKeyFileLineWidget, 2, 1, 1, 1)

        self.authenticationCredentialsWidgetLayout.addWidget(noAuthLabel)
        self.authenticationCredentialsWidgetLayout.addWidget(usernameAndPasswordWidget)
        self.authenticationCredentialsWidgetLayout.addWidget(usernameAndKeyWidget)

        cancelButton = QtWidgets.QPushButton('Cancel')
        cancelButton.clicked.connect(self.reject)
        confirmButton = QtWidgets.QPushButton('Confirm')
        confirmButton.clicked.connect(self.accept)

        layout.addWidget(addSourceLabel, 0, 0, 1, 2)
        layout.addWidget(localOrRemoteSource, 1, 0, 1, 2)
        layout.addWidget(localOrRemoteInput, 2, 0, 1, 2)
        layout.addWidget(self.authenticationOptionWidget, 3, 0, 2, 2)
        layout.addWidget(self.authenticationCredentialsWidget, 5, 0, 2, 2)
        layout.addWidget(cancelButton, 7, 0, 1, 1)
        layout.addWidget(confirmButton, 7, 1, 1, 1)

        self.sourceDict = {}

    def toggleAuthCreds(self, credsOption: int) -> None:
        self.authenticationCredentialsWidgetLayout.setCurrentIndex(credsOption)

    def toggleLocalOrRemote(self) -> None:
        if self.remoteSourceRadioButton.isChecked():
            self.localOrRemoteInputLayout.setCurrentIndex(0)
            self.authenticationOptionWidget.setDisabled(False)
            self.authenticationCredentialsWidget.setDisabled(False)
        else:
            self.authenticationOptionWidget.setDisabled(True)
            self.authenticationCredentialsWidget.setDisabled(True)
            self.noAuthentication.setChecked(True)
            self.localOrRemoteInputLayout.setCurrentIndex(1)
            self.authenticationCredentialsWidgetLayout.setCurrentIndex(0)

    def selectLocalSourceFolder(self) -> None:
        sourceFolderDialog = QtWidgets.QFileDialog()
        sourceFolderDialog.setOption(QtWidgets.QFileDialog.Option.DontUseNativeDialog, True)
        sourceFolderDialog.setViewMode(QtWidgets.QFileDialog.ViewMode.List)
        sourceFolderDialog.setFileMode(QtWidgets.QFileDialog.FileMode.Directory)
        sourceFolderDialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptOpen)
        sourceFolderDialog.setDirectory(str(Path.home()))

        if sourceFolderDialog.exec():
            folderPath = Path(sourceFolderDialog.selectedFiles()[0])
            if folderPath.exists():
                self.localSourceInput.setText(str(folderPath))

    def selectLocalPrivateKeyFile(self) -> None:
        keyFileDialog = QtWidgets.QFileDialog()
        keyFileDialog.setOption(QtWidgets.QFileDialog.Option.DontUseNativeDialog, True)
        keyFileDialog.setViewMode(QtWidgets.QFileDialog.ViewMode.List)
        keyFileDialog.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFile)
        keyFileDialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptOpen)
        keyFileDialog.setDirectory(str(Path.home()))

        if keyFileDialog.exec():
            filePath = Path(keyFileDialog.selectedFiles()[0])
            if filePath.exists():
                self.privateKeyInputField.setText(str(filePath))

    def selectLocalPublicKeyFile(self) -> None:
        keyFileDialog = QtWidgets.QFileDialog()
        keyFileDialog.setOption(QtWidgets.QFileDialog.Option.DontUseNativeDialog, True)
        keyFileDialog.setViewMode(QtWidgets.QFileDialog.ViewMode.List)
        keyFileDialog.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFile)
        keyFileDialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptOpen)
        keyFileDialog.setDirectory(str(Path.home()))

        if keyFileDialog.exec():
            filePath = Path(keyFileDialog.selectedFiles()[0])
            if filePath.exists():
                self.publicKeyInputField.setText(str(filePath))

    def accept(self) -> None:
        self.sourceDict['Remote'] = not self.localSourceRadioButton.isChecked()
        if self.noAuthentication.isChecked():
            self.sourceDict['Auth'] = None
        elif self.usernameAndPassword.isChecked():
            self.sourceDict['Auth'] = (self.usernameInputField.text(), self.passwordInputField.text())
        else:
            self.sourceDict['Auth'] = (self.keyUsernameInputField.text(),
                                       Path(self.privateKeyInputField.text()),
                                       Path(self.publicKeyInputField.text()))
        self.sourceDict['URI'] = self.remoteSourceInput.text() \
            if self.sourceDict['Remote'] else self.localSourceInput.text()
        super().accept()


class ModulePacksListViewer(QtWidgets.QDialog):
    moduleInstallationCompleteSignal = QtCore.Signal()

    def __init__(self, parent: ModulesManager):
        super().__init__()
        self.moduleWidgetBeingInstalled = None
        self.modulesManager = parent

        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)
        self.setWindowTitle('Modules Manager')

        installedModulesLabel = QtWidgets.QLabel("Module Packs")
        installedModulesLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        modulesDescLabel = QtWidgets.QLabel("Double-click a Module Pack to inspect the modules contained in it.")
        modulesDescLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.modulePackList = QtWidgets.QListWidget()
        self.modulePackList.setSelectionMode(self.modulePackList.SelectionMode.SingleSelection)
        addModulePackButton = QtWidgets.QPushButton('Install Module Pack')
        addModulePackButton.clicked.connect(self.addModulePackPrompt)
        removeModulePackButton = QtWidgets.QPushButton('Uninstall Module Pack')
        removeModulePackButton.clicked.connect(self.removeModulePack)

        closeButton = QtWidgets.QPushButton('Close')
        closeButton.clicked.connect(self.accept)

        layout.addWidget(installedModulesLabel, 0, 0, 1, 2)
        layout.addWidget(modulesDescLabel, 1, 0, 1, 2)
        layout.addWidget(self.modulePackList, 2, 0, 3, 2)
        layout.addWidget(removeModulePackButton, 5, 0, 1, 1)
        layout.addWidget(addModulePackButton, 5, 1, 1, 1)
        layout.addWidget(closeButton, 6, 0, 1, 2)

        # Sort module packs alphabetically.
        allPacksDict = {}
        for source in self.modulesManager.modulePacks:
            for module, moduleDetails in self.modulesManager.modulePacks[source].items():
                newItemWidget = ModulePacksListItem(self, moduleDetails)
                newItem = QtWidgets.QListWidgetItem()
                newItem.setSizeHint(newItemWidget.sizeHint())
                allPacksDict[newItemWidget] = (moduleDetails['label'], newItem)
        allPacksDict = dict(sorted(allPacksDict.items(), key=lambda item: item[1][0]))
        for itemWidget, value in allPacksDict.items():
            self.modulePackList.addItem(value[1])
            self.modulePackList.setItemWidget(value[1], itemWidget)
        self.setMinimumWidth(350)
        layout.setRowStretch(3, 10)

    def removeModulePack(self) -> bool:
        try:
            itemToRemove = self.modulePackList.selectedItems()[0]
            widgetOfItem: ModulePacksListItem = self.modulePackList.itemWidget(itemToRemove)
        except IndexError:
            return True

        self.modulesManager.removeModulePack(widgetOfItem.modulePackDict)
        self.moduleWidgetBeingInstalled = widgetOfItem
        widgetOfItem.installedLabel.setText("Uninstalling...")

    def addModulePackPrompt(self) -> None:
        try:
            itemToAdd = self.modulePackList.selectedItems()[0]
            widgetOfItem: ModulePacksListItem = self.modulePackList.itemWidget(itemToAdd)
        except IndexError:
            return

        if widgetOfItem.modulePackDict['Installed']:
            self.modulesManager.mainWindow.MESSAGEHANDLER.warning(
                f'Module "{widgetOfItem.modulePackDict["label"]}" is already Installed.', popUp=True, exc_info=False)
        elif AddModulePackDialog(self, widgetOfItem.modulePackDict, False).exec():
            self.moduleWidgetBeingInstalled = widgetOfItem
            widgetOfItem.installedLabel.setText("Installed: Pending")

    def installModulePack(self, sourceUUID: str, modulePackUUID: str) -> None:
        packDetails = self.modulesManager.modulePacks[sourceUUID][modulePackUUID]
        self.modulesManager.mainWindow.MESSAGEHANDLER.info(
            f'Adding Module Pack: "{packDetails["label"]}" by {packDetails["author"]}')
        self.modulesManager.installModulePackInit(sourceUUID, modulePackUUID)

    def setInstallCompletedForModulePackWidget(self):
        if self.moduleWidgetBeingInstalled is not None:
            self.moduleWidgetBeingInstalled.installedLabel.setText("Installed: True")
            self.moduleWidgetBeingInstalled = None

    def setUninstallCompletedForModulePackWidget(self):
        if self.moduleWidgetBeingInstalled is not None:
            self.moduleWidgetBeingInstalled.installedLabel.setText("Installed: False")
            self.moduleWidgetBeingInstalled = None


class ModulePacksListItem(QtWidgets.QWidget):

    def __init__(self, modulePacksListViewer, modulePackDict: dict):
        super().__init__()
        self.modulePacksListViewer = modulePacksListViewer
        self.modulePackDict = modulePackDict

        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)
        self.modules = modulePackDict['modules']

        author = f"By: {modulePackDict['author']}"
        label = modulePackDict['label']
        installed = f"Installed: {modulePackDict['Installed']}"

        svgRenderer = QtSvg.QSvgRenderer(QtCore.QByteArray(b64decode(modulePackDict['icon'])))
        pixmap = QtGui.QPixmap(60, 60)
        pixmap.fill(QtGui.QColor(0, 0, 0, 0))
        painter = QtGui.QPainter(pixmap)
        svgRenderer.render(painter)
        painter.end()

        sourceImage = QtWidgets.QLabel()
        sourceImage.setPixmap(pixmap)
        layout.addWidget(sourceImage, 0, 0, 4, 4)
        labelLabel = QtWidgets.QLabel(label)
        labelLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        labelLabel.setFont(QtGui.QFont('Times-Bold', 13, QtGui.QFont.Weight.Bold))
        layout.addWidget(labelLabel, 1, 4, 1, 1)
        authorLabel = QtWidgets.QLabel(author)
        authorLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        authorLabel.setFont(QtGui.QFont('Times-Bold', 12, QtGui.QFont.Weight.Bold))
        layout.addWidget(authorLabel, 2, 4, 1, 1)
        self.installedLabel = QtWidgets.QLabel(installed)
        layout.addWidget(self.installedLabel, 4, 0, 1, 5)
        layout.setColumnStretch(4, 10)
        layout.setColumnStretch(3, 0)
        layout.setColumnStretch(2, 0)
        layout.setColumnStretch(1, 0)
        layout.setColumnStretch(0, 0)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        AddModulePackDialog(self.modulePacksListViewer, self.modulePackDict).exec()
        super().mouseDoubleClickEvent(event)


class AddModulePackDialog(QtWidgets.QDialog):

    def __init__(self, modulePacksListViewer: ModulePacksListViewer, moduleDetails: dict, onlyDetails: bool = True):
        super().__init__()
        self.moduleDetails = moduleDetails
        self.modulePacksListViewer = modulePacksListViewer

        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)

        descriptionLabel = QtWidgets.QLabel(moduleDetails['description'])
        descriptionLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        descriptionLabel.setWordWrap(True)

        modulesListLabel = QtWidgets.QLabel('Modules in Module Pack:')
        modulesListLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        modulesList = QtWidgets.QListWidget()
        modulesList.addItems(moduleDetails['modules'])

        installPackButton = QtWidgets.QPushButton('Install')
        installPackButton.clicked.connect(self.accept)
        closeButton = QtWidgets.QPushButton('Close')
        closeButton.clicked.connect(self.reject)

        layout.addWidget(descriptionLabel, 0, 0, 1, 2)
        layout.addWidget(modulesListLabel, 1, 0, 1, 2)
        layout.addWidget(modulesList, 2, 0, 3, 2)

        if onlyDetails:
            self.setWindowTitle('Module Pack Details')
            layout.addWidget(closeButton, 5, 0, 1, 2)
        else:
            self.setWindowTitle('Install Module Pack')
            layout.addWidget(closeButton, 5, 0, 1, 1)
            layout.addWidget(installPackButton, 5, 1, 1, 1)
            closeButton.setText('Cancel')
        layout.setRowStretch(4, 10)

    def accept(self) -> None:
        self.modulePacksListViewer.installModulePack(self.moduleDetails['Source UUID'], self.moduleDetails['UUID'])
        super().accept()


class InitialiseVenvThread(QtCore.QThread):
    configureVenvOfMainThreadSignal = QtCore.Signal(Path)

    def __init__(self, modulesManager: ModulesManager) -> None:
        super().__init__()
        self.modulesManager = modulesManager

    def run(self) -> None:
        venvPath = self.modulesManager.modulesBaseDirectoryPath
        if not (venvPath / 'bin').exists():
            venv.create(venvPath, symlinks=True, with_pip=True, upgrade_deps=True)

        self.configureVenvOfMainThreadSignal.emit(venvPath)


class UpgradeVenvThread(QtCore.QThread):
    upgradeVenvThreadSignal = QtCore.Signal(bool)

    def __init__(self, modulesManager: ModulesManager, useTempFile: bool = False, fullUpgrade: bool = False) -> None:
        super().__init__()
        self.modulesManager = modulesManager
        self.useTempFile = useTempFile
        self.fullUpgrade = fullUpgrade

    def run(self) -> None:
        if self.fullUpgrade:
            for source in self.modulesManager.sources:
                self.modulesManager.syncSource(source, onlySyncExisting=True, showMessages=False)
        if self.useTempFile:
            reqsFile = self.modulesManager.modulesRequirementsTempPath
        else:
            reqsFile = self.modulesManager.modulesRequirementsPath
        try:
            cmdStr = f"'{self.modulesManager.modulesPythonPath}' --version"
            subprocess.check_output(cmdStr, shell=True)
            cmdStr = f"'{self.modulesManager.modulesPythonPath}' -m pip install --upgrade -r '{reqsFile}'"
            subprocess.check_output(cmdStr, shell=True)
            # Install / upgrade playwright & misc if not already installed, since they need special treatment.
            cmdStr = f"'{self.modulesManager.modulesPythonPath}' -m pip install --upgrade pip wheel setuptools playwright"
            subprocess.run(cmdStr, shell=True)
            cmdStr = f"'{self.modulesManager.modulesPythonPath}' -m playwright install"
            subprocess.run(cmdStr, shell=True)
            self.upgradeVenvThreadSignal.emit(True)
        except subprocess.CalledProcessError:
            self.upgradeVenvThreadSignal.emit(False)


class InstallRequirementsThread(QtCore.QThread):
    progressSignal = QtCore.Signal(int)
    installFinishedSignal = QtCore.Signal(bool, str, str, str)

    def __init__(self, modulesManager: ModulesManager, sourceUUID: str, modulePackUUID: str):
        super().__init__()
        self.modulesManager = modulesManager
        self.sourceUUID = sourceUUID
        self.modulePackUUID = modulePackUUID

    def run(self) -> None:
        packDetails = self.modulesManager.modulePacks[self.sourceUUID][self.modulePackUUID]
        modulePackLabel = packDetails['label']

        if packDetails['Installed']:
            self.progressSignal.emit(3)
            self.installFinishedSignal.emit(False, modulePackLabel, "", "")
            return

        requirementsSet = set()
        for module in packDetails['modules']:
            modulePath = self.modulesManager.modulesBaseDirectoryPath / self.sourceUUID / module
            moduleRequirements = modulePath / 'requirements.txt'
            with open(moduleRequirements, 'r') as file:
                [requirementsSet.add(line) for line in file.read().splitlines() if not line.startswith('#')]

        with open(self.modulesManager.modulesRequirementsPath, 'r') as reqFile:
            [requirementsSet.add(line) for line in reqFile.read().splitlines() if not line.startswith('#')]

        with open(self.modulesManager.modulesRequirementsTempPath, 'w') as file:
            [file.write(line + '\n') for line in requirementsSet]

        self.progressSignal.emit(1)

        success = False
        cmdStr = f"'{self.modulesManager.modulesPythonPath}' -m pip install --upgrade -r " \
                 f"'{self.modulesManager.modulesRequirementsTempPath}'"
        try:
            subprocess.check_output(cmdStr, shell=True)

            shutil.move(self.modulesManager.modulesRequirementsTempPath, self.modulesManager.modulesRequirementsPath)
            success = True
        except subprocess.CalledProcessError as cpe:
            # TODO: test
            self.modulesManager.mainWindow.errorSignalListener.emit(
                f'Error occurred while installing Module Pack "{modulePackLabel}":\n{cpe}', True, False)
            self.modulesManager.modulesRequirementsTempPath.unlink(missing_ok=True)
        finally:
            self.progressSignal.emit(3)

        if success:
            self.modulesManager.modulePacks[self.sourceUUID][self.modulePackUUID]['Installed'] = True
            self.installFinishedSignal.emit(True, modulePackLabel, self.sourceUUID, self.modulePackUUID)
        else:
            self.installFinishedSignal.emit(False, modulePackLabel, "", "")


class UninstallModuleThread(QtCore.QThread):
    progressSignal = QtCore.Signal(int)
    uninstallFinishedSignal = QtCore.Signal(bool, str)

    def __init__(self, modulesManager: ModulesManager, modulePackDict: dict):
        super().__init__()
        self.modulesManager = modulesManager
        self.modulePackDict = modulePackDict

    def run(self) -> None:
        modulePackLabel = self.modulePackDict['label']
        modulePackSourceUUID = self.modulePackDict['Source UUID']
        modulePackUUID = self.modulePackDict['UUID']

        if not self.modulePackDict['Installed']:
            self.progressSignal.emit(3)
            self.uninstallFinishedSignal.emit(False, modulePackLabel)
            return

        newRequirementsSet = set()
        for sourceDict in self.modulesManager.sources.values():
            sourceUUID = sourceDict['UUID']
            for modulePackDetails in self.modulesManager.modulePacks[sourceUUID].values():
                if modulePackUUID == modulePackDetails['UUID'] and \
                        modulePackSourceUUID == modulePackDetails['Source UUID']:
                    pass
                elif modulePackDetails['Installed']:
                    for module in modulePackDetails['modules']:
                        moduleReqsPath = self.modulesManager.modulesBaseDirectoryPath / sourceUUID / module / 'requirements.txt'
                        with open(moduleReqsPath, 'r') as file:
                            [newRequirementsSet.add(line) for line in file.read().splitlines()
                             if not line.startswith('#')]

        with open(self.modulesManager.modulesRequirementsPath, 'r') as reqsFile:
            allRequirementsSet = {line for line in reqsFile.read().splitlines() if not line.startswith('#')}

        with open(self.modulesManager.modulesRequirementsTempPath, 'w') as file:
            [file.write(line + '\n') for line in newRequirementsSet]

        if reqsDiff := allRequirementsSet.difference(newRequirementsSet):
            cmdStr = f"'{self.modulesManager.modulesPythonPath}' -m pip uninstall {' '.join(reqsDiff)} -y"
            try:
                subprocess.check_output(cmdStr, shell=True)
                shutil.move(self.modulesManager.modulesRequirementsTempPath,
                            self.modulesManager.modulesRequirementsPath)
            except subprocess.CalledProcessError as cpe:
                self.modulesManager.mainWindow.errorSignalListener.emit(
                    f'Error occurred while uninstalling Module Pack "{modulePackLabel}":\n{cpe}', True, False)
                self.modulesManager.modulesRequirementsTempPath.unlink(missing_ok=True)
                self.progressSignal.emit(3)
                self.uninstallFinishedSignal.emit(True, modulePackLabel)
                return

        self.modulesManager.modulePacks[modulePackSourceUUID][modulePackUUID]['Installed'] = False

        self.progressSignal.emit(3)
        self.uninstallFinishedSignal.emit(True, modulePackLabel)


class AuthType(int, Enum):
    NONE = 0
    PASSWORD = 1
    KEY = 2


class SchemaType(int, Enum):
    LOCAL = 0
    HTTPS = 1
    SSH = 2
    GIT = 3
