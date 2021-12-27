#!/usr/bin/env python3

import re
import json
import platform
import os

import magic
import lz4.block
import pandas as pd
import webbrowser
from urllib import parse
from pathlib import Path

from playwright.sync_api import sync_playwright, Error

from PySide6 import QtWidgets, QtGui, QtCore

from Core.Interface import Stylesheets
from Core.Interface.Entity import BaseNode


class MenuBar(QtWidgets.QMenuBar):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        fileMenu = self.addMenu("File")
        fileMenu.setStyleSheet(Stylesheets.MENUS_STYLESHEET_2)

        saveAction = QtGui.QAction("&Save",
                                   self,
                                   statusTip="Save The Project",
                                   triggered=self.save)
        saveAction.setShortcut("Ctrl+S")
        fileMenu.addAction(saveAction)

        saveAsAction = QtGui.QAction("Save As",
                                     self,
                                     statusTip="Save the Project in a new directory, under a new name.",
                                     triggered=self.saveAs)
        fileMenu.addAction(saveAsAction)

        renameAction = QtGui.QAction("Rename Project",
                                     self,
                                     statusTip="Rename the Project.",
                                     triggered=self.rename)
        fileMenu.addAction(renameAction)

        importMenu = self.addMenu("Import")
        importMenu.setStyleSheet(Stylesheets.MENUS_STYLESHEET_2)

        fromBrowserAction = QtGui.QAction("From Browser",
                                          self,
                                          statusTip="Import open tabs as Website and materials entities.",
                                          triggered=self.importFromBrowser)

        fromFileAction = QtGui.QAction("From File",
                                       self,
                                       statusTip="Import entities from a file.",
                                       triggered=self.importFromFile)

        graphMLCanvasAction = QtGui.QAction("GraphML - Canvas",
                                            self,
                                            statusTip="Import canvas from a GraphML file.",
                                            triggered=self.parent().importCanvasFromGraphML)

        graphMLDatabaseAction = QtGui.QAction("GraphML - Database",
                                              self,
                                              statusTip="Import database from a GraphML file.",
                                              triggered=self.parent().importDatabaseFromGraphML)
        importMenu.addAction(fromBrowserAction)
        importMenu.addAction(fromFileAction)
        importMenu.addAction(graphMLCanvasAction)
        importMenu.addAction(graphMLDatabaseAction)

        exportMenu = self.addMenu("Export")
        exportMenu.setStyleSheet(Stylesheets.MENUS_STYLESHEET_2)

        canvasPictureAction = QtGui.QAction("Save Picture of Canvas", self,
                                            statusTip="Save a picture of your canvas",
                                            triggered=self.savePic)
        GraphMLCanvas = QtGui.QAction('GraphML - Canvas ',
                                      self,
                                      statusTip="Export Canvas to GraphML",
                                      triggered=self.parent().exportCanvasToGraphML)

        GraphMLDatabase = QtGui.QAction('GraphML - Database ',
                                        self,
                                        statusTip="Export Database to GraphML",
                                        triggered=self.parent().exportDatabaseToGraphML)
        exportMenu.addAction(canvasPictureAction)
        exportMenu.addAction(GraphMLCanvas)
        exportMenu.addAction(GraphMLDatabase)

        editSettingsMenu = fileMenu.addMenu("Edit Settings")
        editLog = QtGui.QAction('Logging Settings',
                                self,
                                statusTip="Edit Logging Settings",
                                triggered=self.editLogSettings)

        editProject = QtGui.QAction('Project Settings',
                                    self,
                                    statusTip="Edit Project Settings",
                                    triggered=self.editProjectSettings)

        editResolution = QtGui.QAction('Resolutions Settings',
                                       self,
                                       statusTip="Edit Resolutions Settings",
                                       triggered=self.editResolutionsSettings)

        editSettingsMenu.addAction(editLog)
        editSettingsMenu.addAction(editResolution)
        editSettingsMenu.addAction(editProject)

        exitAction = QtGui.QAction("Exit",
                                   self,
                                   statusTip="Save, Close Project and Exit",
                                   triggered=self.exitSoftware)
        fileMenu.addAction(exitAction)

        viewMenu = self.addMenu("View")
        viewMenu.setStyleSheet(Stylesheets.MENUS_STYLESHEET_2)

        saveAction = QtGui.QAction("&Find",
                                   self,
                                   statusTip="Find Links or Entities",
                                   triggered=self.findEntityOrLink)
        saveAction.setShortcut("Ctrl+F")
        viewMenu.addAction(saveAction)

        runningResolutiosAction = QtGui.QAction("&Running Resolutions",
                                                self,
                                                statusTip="View Running Resolutions",
                                                triggered=self.runningResolutions)
        runningResolutiosAction.setShortcut("Ctrl+R")
        viewMenu.addAction(runningResolutiosAction)

        dockbarVisibilityMenu = viewMenu.addMenu("Toggle Dockbar Visibility")

        self.dockbarOneVisibilityAction = QtGui.QAction("Toggle Dockbar One",
                                                        self,
                                                        statusTip="Toggle the visibility of Dockbar One",
                                                        triggered=self.toggleDockbarOneVisibility)
        dockbarVisibilityMenu.addAction(self.dockbarOneVisibilityAction)

        self.dockbarTwoVisibilityAction = QtGui.QAction("Toggle Dockbar Two",
                                                        self,
                                                        statusTip="Toggle the visibility of Dockbar Two",
                                                        triggered=self.toggleDockbarTwoVisibility)
        dockbarVisibilityMenu.addAction(self.dockbarTwoVisibilityAction)

        self.dockbarThreeVisibilityAction = QtGui.QAction("Toggle Dockbar Three",
                                                          self,
                                                          statusTip="Toggle the visibility of Dockbar Three",
                                                          triggered=self.toggleDockbarThreeVisibility)
        dockbarVisibilityMenu.addAction(self.dockbarThreeVisibilityAction)

        toolbarVisibilityMenu = viewMenu.addMenu("Toggle Toolbar Visibility")
        self.primaryToolbarVisibilityAction = QtGui.QAction("Toggle Primary Toolbar",
                                                            self,
                                                            statusTip="Toggle the visibility of the Primary Toolbar",
                                                            triggered=self.togglePrimaryToolbarVisibility)
        toolbarVisibilityMenu.addAction(self.primaryToolbarVisibilityAction)

        modulesMenu = self.addMenu("Modules")
        modulesMenu.setStyleSheet(Stylesheets.MENUS_STYLESHEET_2)

        reloadModulesAction = QtGui.QAction("Reload Modules", self,
                                            statusTip="Reload all Entities and Transforms from Modules",
                                            triggered=self.reloadModules)
        modulesMenu.addAction(reloadModulesAction)

        serverMenu = self.addMenu("&Server")
        serverMenu.setStyleSheet(Stylesheets.MENUS_STYLESHEET_2)

        connectAction = QtGui.QAction("Connect", self,
                                      statusTip="Connect to a Server",
                                      triggered=self.serverConnectionWizard)
        serverMenu.addAction(connectAction)

        disconnectAction = QtGui.QAction("Disconnect", self,
                                         statusTip="Disconnect from any connected server",
                                         triggered=self.disconnectFromServer)
        serverMenu.addAction(disconnectAction)

        serverMenu.addSeparator()

        createOrOpenProject = QtGui.QAction("Create or Open Project", self,
                                            statusTip="Create or Open a new Server project.",
                                            triggered=self.serverOpenOrCreateProject)
        serverMenu.addAction(createOrOpenProject)

        serverMenu.addSeparator()

        syncCanvasAction = QtGui.QAction("Sync Current Canvas", self,
                                         statusTip="Sync the selected canvas with the server's version, or create "
                                                   "it on the server if it does not exist.",
                                         triggered=self.syncCurrentCanvas)
        serverMenu.addAction(syncCanvasAction)

        unSyncCanvasAction = QtGui.QAction("UnSync Current Canvas", self,
                                           statusTip="UnSync the selected canvas from the server's version.",
                                           triggered=self.unSyncCurrentCanvas)
        serverMenu.addAction(unSyncCanvasAction)

        serverMenu.addSeparator()

        reSyncDatabase = QtGui.QAction("Force Re-Sync Database", self,
                                       statusTip="Re-Sync the project's local database with the server's version.",
                                       triggered=self.forceDatabaseSync)
        serverMenu.addAction(reSyncDatabase)

        reloadServerResolutionsAction = QtGui.QAction("Reload Server Resolutions", self,
                                                      statusTip="Reload resolutions from server",
                                                      triggered=self.reloadServerResolutions)
        serverMenu.addAction(reloadServerResolutionsAction)

        reloadServerProjectsAction = QtGui.QAction("Reload Server Projects List", self,
                                                   statusTip="Reload the list of projects made available "
                                                             "by the server. WARNING: Will disconnect from "
                                                             "current project, if any.",
                                                   triggered=self.reloadServerProjectsList)
        serverMenu.addAction(reloadServerProjectsAction)

        reloadServerProjectCanvasesAction = QtGui.QAction("Reload Server Project Canvases List", self,
                                                          statusTip="Reload the list of canvases for the current "
                                                                    "server project. WARNING: Will unsync "
                                                                    "currently synced canvases, if any.",
                                                          triggered=self.reloadServerProjectCanvasesList)
        serverMenu.addAction(reloadServerProjectCanvasesAction)

        reloadServerProjectFilesAction = QtGui.QAction("Reload Server Project Files List", self,
                                                       statusTip="Reload the list of files for the current "
                                                                 "server project",
                                                       triggered=self.reloadServerProjectFilesList)
        serverMenu.addAction(reloadServerProjectFilesAction)

        serverMenu.addSeparator()

        uploadFilesAction = QtGui.QAction("Upload Selected Files", self,
                                          statusTip="Upload selected Materials entity files to server",
                                          triggered=self.uploadFiles)
        serverMenu.addAction(uploadFilesAction)

        downloadFileAction = QtGui.QAction("Download Files", self,
                                           statusTip="Download specified files from server",
                                           triggered=self.downloadFile)
        serverMenu.addAction(downloadFileAction)

    # Use this function to change the labels of functions when necessary.
    # Not very efficient, but much more intuitive than creating a ton of different menus
    #   and mashing them together.
    def mousePressEvent(self, arg__1: QtGui.QMouseEvent) -> None:
        super(MenuBar, self).mousePressEvent(arg__1)
        self.dockbarOneVisibilityAction.setText("Hide Dockbar One" if self.parent().dockbarOne.isVisible() else
                                                "Show Dockbar One")
        self.dockbarTwoVisibilityAction.setText("Hide Dockbar Two" if self.parent().dockbarTwo.isVisible() else
                                                "Show Dockbar Two")
        self.dockbarThreeVisibilityAction.setText("Hide Dockbar Three" if self.parent().dockbarThree.isVisible() else
                                                  "Show Dockbar Three")
        self.primaryToolbarVisibilityAction.setText("Hide Primary Toolbar"
                                                    if self.parent().primaryToolbar.isVisible() else
                                                    "Show Primary Toolbar")

    def toggleDockbarOneVisibility(self) -> None:
        if self.parent().dockbarOne.isVisible():
            self.parent().dockbarOne.setVisible(False)
        else:
            self.parent().dockbarOne.setVisible(True)

    def toggleDockbarTwoVisibility(self) -> None:
        if self.parent().dockbarTwo.isVisible():
            self.parent().dockbarTwo.setVisible(False)
        else:
            self.parent().dockbarTwo.setVisible(True)

    def toggleDockbarThreeVisibility(self) -> None:
        if self.parent().dockbarThree.isVisible():
            self.parent().dockbarThree.setVisible(False)
        else:
            self.parent().dockbarThree.setVisible(True)

    def togglePrimaryToolbarVisibility(self) -> None:
        if self.parent().primaryToolbar.isVisible():
            self.parent().primaryToolbar.setVisible(False)
        else:
            self.parent().primaryToolbar.setVisible(True)

    def importFromFile(self) -> None:
        importDialog = ImportFromFileDialog(self)
        importDialogAccept = importDialog.exec_()
        return_results = []
        fileDirectory = importDialog.fileDirectory
        if importDialogAccept and fileDirectory != '':
            sceneToAddTo = None
            if importDialog.importToCanvasCheckbox.isChecked():
                sceneToAddTo = self.parent().centralWidget().tabbedPane.getSceneByName(
                    importDialog.importToCanvasDropdown.currentText())
            if importDialog.CSVFileChoice.isChecked():
                try:
                    csvContents = pd.read_csv(fileDirectory, usecols=['EntityType', 'EntityField', 'EntityValue'])
                    for entity in range(len(csvContents['EntityType'])):
                        if csvContents['EntityType'][entity] in self.parent().RESOURCEHANDLER.getAllEntities():
                            if csvContents['EntityField'][entity] in list(
                                    self.parent().RESOURCEHANDLER.getEntityJson(csvContents['EntityType'][entity])):
                                return_results.append(
                                    [{csvContents['EntityField'][entity]: str(csvContents['EntityValue'][entity]),
                                      'Entity Type': csvContents['EntityType'][entity]}])
                            else:
                                self.parent().MESSAGEHANDLER.warning(
                                    'Please Check that the format of the csv provided is as described by '
                                    f'the documentation. Malformed entity detected at line {entity + 1}. The '
                                    f'field of the entity is Invalid', popUp=True)
                        else:
                            self.parent().MESSAGEHANDLER.warning(
                                "Please Check that the format of the csv provided is as described by "
                                f"the documentation. Malformed entity detected at line {entity + 1}. The "
                                f"entity type is Invalid", popUp=True)
                except ValueError:
                    self.parent().MESSAGEHANDLER.warning("Please check that the format of the csv provided is as "
                                                         "described by the documentation. It should have 3 columns in "
                                                         "order of EntityType, EntityField, EntityValue. All the "
                                                         "'Values' should be filled accordingly", popUp=True)
                    return_results = []
            elif importDialog.textFileChoice.isChecked():
                importDialog = ImportFromTextFileDialog(self)
                if importDialog.exec_():
                    txtFileContents = open(fileDirectory, 'r')
                    selectedEntityType = importDialog.importTypeDropdown.currentText()
                    jsonOfField = self.parent().RESOURCEHANDLER.getEntityJson(selectedEntityType)
                    primary_field = list(jsonOfField)[1]
                    for line in txtFileContents.readlines():
                        if re.match(r'\w', line):
                            return_results.append(
                                [{primary_field: line,
                                  'Entity Type': selectedEntityType}])
            newNodeUIDs = []
            newLinks = []
            for newNode in return_results:
                newNodeJson = self.parent().LENTDB.addEntity(newNode[0])
                if newNodeJson is not None:
                    newNodeUIDs.append(newNodeJson['uid'])
                else:
                    newNodeUIDs.append(None)

            self.parent().centralWidget().tabbedPane.linkAddHelper(newLinks)

            if sceneToAddTo is not None:
                for newNodeUID in newNodeUIDs:
                    if newNodeUID is not None:
                        sceneToAddTo.addNodeProgrammatic(newNodeUID)
                sceneToAddTo.rearrangeGraph()

    def savePic(self) -> None:
        canvasSaveDialog = CanvasPictureDialog(self)
        canvasSaveDialogAccept = canvasSaveDialog.exec_()
        fileDirectory = canvasSaveDialog.fileDirectory

        if canvasSaveDialogAccept and fileDirectory != '':
            canvas = canvasSaveDialog.chosenCanvasDropdown.currentText()
            transparentBackground = False
            justViewport = True
            if canvasSaveDialog.transparentChoice.isChecked():
                transparentBackground = True
            picture = self.parent().getPictureOfCanvas(canvas, justViewport, transparentBackground)
            picture.save(fileDirectory, "PNG")

    def save(self) -> None:
        self.parent().saveProject()

    def saveAs(self) -> None:
        self.parent().saveAsProject()

    def rename(self) -> None:
        self.parent().renameProjectPromptName()

    def editSettings(self) -> None:
        self.parent().editSettings()

    def editLogSettings(self) -> None:
        self.parent().editLogSettings()

    def editProjectSettings(self) -> None:
        self.parent().editProjectSettings()

    def editResolutionsSettings(self) -> None:
        self.parent().editResolutionsSettings()

    def exitSoftware(self) -> None:
        self.parent().close()

    def reloadModules(self) -> None:
        self.parent().reloadModules()

    def runningResolutions(self) -> None:
        self.parent().cleanUpLocalFinishedResolutions()
        runningResolutionsDialog = ViewAndStopResolutionsDialog(self.parent())
        runningResolutionsDialog.exec()

    # Server Operations
    def serverConnectionWizard(self) -> None:
        serverWizard = ServerConnectWizard(self)
        serverWizard.exec_()

        serverPassword = serverWizard.serverPasswordTextbox.text()
        serverIP = serverWizard.serverIPTextbox.text()
        serverPort = int(serverWizard.serverPortTextbox.text())

        if not serverWizard.confirmConnect:
            self.parent().MESSAGEHANDLER.debug("Cancelled connecting to server")
            return

        if isinstance(serverPassword, str) and \
                isinstance(serverIP, str) and \
                isinstance(serverPort, int) and \
                0 < serverPort < 65535:
            self.parent().connectToServer(serverPassword, serverIP, serverPort)
        else:
            self.parent().MESSAGEHANDLER.info("Invalid Information Provided",
                                              popUp=True)

    def disconnectFromServer(self) -> None:
        self.parent().disconnectFromServer()

    def serverOpenOrCreateProject(self) -> None:
        if self.parent().FCOM.isConnected():
            serverProjectDialog = ServerCreateOrOpenProject(self.parent())
            createOrOpenProject = serverProjectDialog.exec()

            if createOrOpenProject:
                if serverProjectDialog.openProject:
                    self.parent().FCOM.openProject(serverProjectDialog.projectName,
                                                   serverProjectDialog.projectPass)
                else:
                    self.parent().FCOM.createProject(serverProjectDialog.projectName,
                                                     serverProjectDialog.projectPass)
        else:
            self.parent().MESSAGEHANDLER.warning('Not Connected to Server!', popUp=True)
            self.parent().setStatus('Must connect to a server before opening a project.')

    # For canvas stuff, check if canvas name exists.
    def syncCurrentCanvas(self) -> None:
        self.parent().syncCanvasByName()

    def unSyncCurrentCanvas(self) -> None:
        self.parent().unSyncCurrentCanvas()

    def reloadServerResolutions(self) -> None:
        if self.parent().FCOM.isConnected():
            self.parent().RESOLUTIONMANAGER.removeServerResolutions()
            self.parent().dockbarOne.resolutionsPalette.loadAllResolutions()
            self.parent().FCOM.askServerForResolutions()

    def reloadServerProjectsList(self) -> None:
        if self.parent().FCOM.isConnected():
            if self.parent().SETTINGS.value("Project/Server/Project") != '':
                self.parent().closeCurrentServerProject()
                self.parent().receiveProjectsListListener([])
            self.parent().FCOM.askProjectsList()

    def reloadServerProjectCanvasesList(self) -> None:
        if self.parent().FCOM.isConnected():
            project_name = self.parent().SETTINGS.value("Project/Server/Project")
            self.parent().unSyncCanvasByName(None)
            self.parent().receiveProjectCanvasesListListener([])
            self.parent().FCOM.askProjectCanvasesList(project_name)

    def reloadServerProjectFilesList(self):
        if self.parent().FCOM.isConnected():
            project_name = self.parent().SETTINGS.value("Project/Server/Project")
            self.parent().receiveFileListListener([])
            self.parent().FCOM.askServerForFileList(project_name)

    def forceDatabaseSync(self) -> None:
        if self.parent().FCOM.isConnected():
            project_name = self.parent().SETTINGS.value("Project/Server/Project")
            with self.parent().LENTDB.dbLock:
                self.parent().FCOM.syncDatabase(project_name, self.parent().LENTDB.database)

    def uploadFiles(self) -> None:
        self.parent().uploadFiles()

    def downloadFile(self):
        pass

    def findEntityOrLink(self) -> None:
        self.parent().findEntityOrLinkOnCanvas()

    def openWebsite(self) -> None:
        currentScene = self.parent().centralWidget().tabbedPane.getCurrentScene()
        websites = [item.uid for item in currentScene.selectedItems()
                    if isinstance(item, BaseNode) and
                    self.parent().LENTDB.getEntity(item.uid)['Entity Type'] == 'Website']
        for website in websites:
            webbrowser.open(website[list(website)[1]], new=0, autoraise=True)

    def importFromBrowser(self) -> None:
        """
        Import session tabs to canvas. Optionally, also take a screenshot of them.
        Assumes default browser profiles.

        :return:
        """
        if platform.system() != 'Linux' and platform.system() != 'Windows':
            self.parent().setStatus('Importing tabs not supported on platforms other than Linux and Windows.')
            self.parent().MESSAGEHANDLER.warning('Importing tabs not supported on platforms '
                                                 'other than Linux and Windows.', popUp=True)
            return

        importDialog = BrowserImportDialog(self)

        if importDialog.exec_():

            steps = 4
            progress = QtWidgets.QProgressDialog('Importing tabs, please wait...',
                                                 'Abort Import', 0, steps, self)
            progress.setWindowModality(QtCore.Qt.WindowModal)
            progress.setMinimumDuration(0)

            returnResults = []

            progress.setValue(1)
            with sync_playwright() as p:
                if importDialog.firefoxChoice.isChecked():
                    try:
                        browser = p.firefox.launch()

                        if platform.system() == 'Linux':
                            context = browser.new_context(
                                viewport={'width': 1920, 'height': 1080},
                                user_agent='Mozilla/5.0 (X11; Linux i686; rv:94.0) Gecko/20100101 Firefox/94.0'
                            )
                            urlPath = Path.home() / '.mozilla' / 'firefox'
                        else:  # We already checked before that the platform is either 'Linux' or 'Windows'.
                            context = browser.new_context(
                                viewport={'width': 1920, 'height': 1080},
                                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 '
                                           'Firefox/94.0'
                            )
                            urlPath = Path(os.environ['APPDATA']) / 'Mozilla' / 'Firefox' / 'Profiles'

                        tabsFilePath = list(urlPath.glob('*default*/sessionstore-backups/recovery.jsonlz4'))
                        if len(tabsFilePath) == 0:
                            self.parent().MESSAGEHANDLER.warning('No Firefox session detected. Skipping importing from'
                                                                 ' Firefox.', popUp=True)
                        else:
                            tabsFilePath = tabsFilePath[0]
                            tabsToOpen = set()

                            tabsBytes = tabsFilePath.read_bytes()
                            if tabsBytes[:8] == b'mozLz40\0':
                                tabsBytes = lz4.block.decompress(tabsBytes[8:])
                            tabsJson = json.loads(tabsBytes)
                            for browserWindow in tabsJson['windows']:
                                for browserTab in browserWindow['tabs']:
                                    if importDialog.firefoxSessionChoice.isChecked():
                                        for browserEntry in browserTab['entries']:
                                            url = browserEntry['url']
                                            if not url.startswith('about:'):
                                                tabsToOpen.add((url, browserEntry['title']))
                                    else:
                                        browserEntry = browserTab['entries'][-1]
                                        url = browserEntry['url']
                                        if not url.startswith('about:'):
                                            tabsToOpen.add((url, browserEntry['title']))

                            browserCookies = []
                            for cookie in tabsJson['cookies']:
                                newCookie = {'name': cookie['name'], 'value': cookie['value'],
                                             'domain': cookie['host'], 'path': cookie['path'],
                                             'httpOnly': cookie.get('httponly', False),
                                             'secure': cookie.get('secure', False)}
                                if cookie.get('expiry', None) is not None:
                                    newCookie['expires'] = float(cookie['expiry'])
                                if cookie.get('sameSite', None) is not None:
                                    newCookie['sameSite'] = cookie['sameSite']
                                browserCookies.append(newCookie)
                            context.add_cookies(browserCookies)
                            page = context.new_page()

                            self.parent().MESSAGEHANDLER.debug('Tabs to open: ' + str(tabsToOpen))
                            projectFilesDir = Path(self.parent().SETTINGS.value("Project/FilesDir"))

                            for tabToOpen in tabsToOpen:
                                urlTitle = tabToOpen[1]
                                actualURL = tabToOpen[0]
                                decodedPath = parse.unquote(actualURL)
                                parsedURL = parse.urlparse(decodedPath)
                                urlPath = parsedURL.path

                                if parsedURL.scheme == 'file':
                                    try:
                                        mime = magic.Magic(mime=True)
                                        pathType = mime.from_file(urlPath)
                                    except FileNotFoundError:
                                        continue

                                    if 'application' in pathType:
                                        returnResults.append([{'Document Name': urlTitle,
                                                               'File Path': urlPath,
                                                               'Entity Type': 'Document'}])
                                    elif 'image' in pathType:
                                        returnResults.append([{'Image Name': urlTitle,
                                                               'File Path': urlPath,
                                                               'Entity Type': 'Image'}])
                                    elif 'video' in pathType:
                                        returnResults.append([{'Video Name': urlTitle,
                                                               'File Path': urlPath,
                                                               'Entity Type': 'Video'}])
                                    elif 'archive' in pathType:
                                        returnResults.append([{'Archive Name': urlTitle,
                                                               'File Path': urlPath,
                                                               'Entity Type': 'Archive'}])

                                elif parsedURL.scheme.startswith('http'):
                                    returnResults.append([{'URL': actualURL,
                                                           'Entity Type': 'Website'}])

                                    if importDialog.importScreenshotsCheckbox.isChecked():
                                        page.goto(actualURL)

                                        urlSaveDir = projectFilesDir / urlTitle

                                        try:
                                            if not urlSaveDir.exists():
                                                urlSaveDir.mkdir(mode=0o700)
                                        except OSError:
                                            urlSaveDir = None

                                        if urlSaveDir is not None:
                                            screenshotSavePath = str(urlSaveDir / (actualURL.replace('/', '+') +
                                                                                   ' screenshot.png'))
                                            page.screenshot(path=screenshotSavePath, full_page=True)

                                            returnResults.append(
                                                [{'Image Name': urlTitle + ' Website Screenshot',
                                                  'File Path': screenshotSavePath,
                                                  'Entity Type': 'Image'},
                                                 {'Resolution': 'Screenshot of Tab', 'Notes': ''}])

                        browser.close()
                    except Error:
                        self.parent().MESSAGEHANDLER.warning('Firefox executable is not installed. Cannot import '
                                                             'tabs from Firefox.', popUp=True)

                progress.setValue(2)
                if importDialog.chromeChoice.isChecked() and not progress.wasCanceled():
                    try:
                        browser = p.chromium.launch()

                        # NOTE: Cookies are not obtained for chromium based browsers.

                        if platform.system() == 'Linux':
                            context = browser.new_context(
                                viewport={'width': 1920, 'height': 1080},
                                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                                           "Chrome/96.0.4664.45 Safari/537.36"
                            )
                            sessionFilePath = Path.home() / '.config' / 'google-chrome' / 'Default' / 'Sessions'
                            if not sessionFilePath.exists():
                                sessionFilePath = Path.home() / 'snap' / 'chromium' / 'common' / 'chromium' / \
                                                  'Default' / 'Sessions'
                        else:  # We already checked before that the platform is either 'Linux' or 'Windows'.
                            context = browser.new_context(
                                viewport={'width': 1920, 'height': 1080},
                                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                           "(KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36"
                            )
                            sessionFilePath = Path.home() / 'AppData' / 'Local' / 'Google' / 'Chrome' / 'User Data' /\
                                              'Default'

                        lastSessionOpenTabs = set()

                        # Get the session file with the largest timestamp (i.e. most recent session)
                        # Need the while loop to prevent race conditions
                        chromeSessionFileContents = None
                        if sessionFilePath.exists():
                            while True:
                                try:
                                    latestTimestamp = max([int(sessionFile.split("Session_", 1)[1])
                                                           for sessionFile in os.listdir(sessionFilePath)
                                                           if 'Session_' in sessionFile])
                                    sessionFilePath = sessionFilePath.joinpath("Session_" + str(latestTimestamp))
                                    chromeSessionFileContents = sessionFilePath.read_bytes()
                                    break
                                except (FileNotFoundError, IndexError):
                                    pass
                                except ValueError:
                                    # No session files means we can't do anything for chrome.
                                    break

                        if chromeSessionFileContents is None:
                            self.parent().MESSAGEHANDLER.warning('Chrome / Chromium session file does not exist or is'
                                                                 ' inaccessible. Cannot import tabs from Chrome /'
                                                                 ' Chromium.', popUp=True)
                        else:
                            projectFilesDir = Path(self.parent().SETTINGS.value("Project/FilesDir"))

                            """
                            WARNING: This is a hackish solution that does not always work. Documentation and tools to work
                                     with chrome and chromium session files are lacking last I checked,
                                     and most of the existing ones have been broken since the last update.
                                     This is a best-effort solution for now, which should mostly work.
            
                                     As for how it works, it's just pattern matching after some observations about the
                                     file structure of chrome session files.
            
                                     This will probably be revised in the future to make it actually parse chrome session
                                     files.
                            """
                            httpTabs = re.split(b'http', chromeSessionFileContents)
                            for httpTab in httpTabs[1:]:
                                try:
                                    tabURL = re.split(b'\x00|\x0b', httpTab)[0].decode()
                                except UnicodeDecodeError:
                                    continue
                                if tabURL.startswith('s://'):
                                    tabURL = 'https://' + tabURL[4:]
                                else:
                                    tabURL = 'http://' + tabURL[3:]
                                if tabURL[-1] == '/':
                                    tabURL = tabURL[:-1]
                                lastSessionOpenTabs.add(tabURL)
                            fileTabs = re.split(b'file', chromeSessionFileContents)
                            for fileTab in fileTabs[1:]:
                                try:
                                    tabURL = 'file://' + re.split(b'\x00|\x0b', fileTab)[0].decode()[3:]
                                except UnicodeDecodeError:
                                    continue
                                lastSessionOpenTabs.add(tabURL)

                            page = context.new_page()
                            for tabURL in lastSessionOpenTabs:
                                decodedPath = parse.unquote(tabURL)
                                parsedURL = parse.urlparse(decodedPath)
                                urlPath = parsedURL.path
                                urlTitle = parsedURL.netloc

                                if parsedURL.scheme == 'file':
                                    urlTitle = Path(urlPath).name
                                    try:
                                        mime = magic.Magic(mime=True)
                                        pathType = mime.from_file(urlPath)
                                    except FileNotFoundError:
                                        continue

                                    if 'application' in pathType:
                                        returnResults.append([{'Document Name': urlTitle,
                                                               'File Path': urlPath,
                                                               'Entity Type': 'Document'}])
                                    elif 'image' in pathType:
                                        returnResults.append([{'Image Name': urlTitle,
                                                               'File Path': urlPath,
                                                               'Entity Type': 'Image'}])
                                    elif 'video' in pathType:
                                        returnResults.append([{'Video Name': urlTitle,
                                                               'File Path': urlPath,
                                                               'Entity Type': 'Video'}])
                                    elif 'archive' in pathType:
                                        returnResults.append([{'Archive Name': urlTitle,
                                                               'File Path': urlPath,
                                                               'Entity Type': 'Archive'}])

                                elif parsedURL.scheme.startswith('http'):
                                    returnResults.append([{'URL': tabURL,
                                                           'Entity Type': 'Website'}])

                                    if importDialog.importScreenshotsCheckbox.isChecked():
                                        page.goto(tabURL)

                                        urlSaveDir = projectFilesDir / urlTitle

                                        try:
                                            if not urlSaveDir.exists():
                                                urlSaveDir.mkdir(mode=0o700)
                                        except OSError:
                                            urlSaveDir = None

                                        if urlSaveDir is not None:
                                            screenshotSavePath = str(urlSaveDir / (
                                                        tabURL.replace('/', '+') + ' screenshot.png'))
                                            page.screenshot(path=screenshotSavePath, full_page=True)

                                            returnResults.append(
                                                [{'Image Name': urlTitle + ' Website Screenshot',
                                                  'File Path': screenshotSavePath,
                                                  'Entity Type': 'Image'},
                                                 {'Resolution': 'Screenshot of Tab', 'Notes': ''}])

                        browser.close()
                    except Error:
                        self.parent().MESSAGEHANDLER.warning('Chrome / Chromium executable is not installed. Cannot '
                                                             'import tabs from Chrome / Chromium.', popUp=True)

            progress.setValue(3)
            newNodeUIDs = []
            newLinks = []
            if progress.wasCanceled():
                progress.setValue(4)
                self.parent().setStatus('Cancelled importing entities from Browser.')
                return

            for newNode in returnResults:
                newNodeJson = self.parent().LENTDB.addEntity(newNode[0])
                if newNodeJson is not None:
                    newNodeUIDs.append(newNodeJson['uid'])
                else:
                    newNodeUIDs.append(None)
                if len(newNode) > 1:
                    parentUID = newNodeUIDs[-2]
                    if parentUID is not None:
                        newLink = (parentUID, newNodeJson['uid'], newNode[1]['Resolution'], newNode[1]['Notes'])
                        newLinks.append(newLink)

            self.parent().centralWidget().tabbedPane.linkAddHelper(newLinks)
            self.parent().setStatus('Imported entities from Browser.')

            if importDialog.importToCanvasCheckbox.isChecked():
                sceneToAddTo = self.parent().centralWidget().tabbedPane.getSceneByName(
                    importDialog.importToCanvasDropdown.currentText())
                for newNodeUID in newNodeUIDs:
                    if newNodeUID is not None:
                        sceneToAddTo.addNodeProgrammatic(newNodeUID)
                sceneToAddTo.rearrangeGraph()
                self.parent().setStatus('Imported entities from Browser into Canvas.')
            progress.setValue(4)


class BrowserImportDialog(QtWidgets.QDialog):

    def __init__(self, parent):
        super(BrowserImportDialog, self).__init__(parent=parent)
        self.setWindowTitle('Import Browser Tabs')
        self.setModal(True)

        dialogLayout = QtWidgets.QGridLayout()
        self.setLayout(dialogLayout)
        descriptionLabel = QtWidgets.QLabel('Choose open browser(s) to import tabs from. Note that support'
                                            ' for chromium-based browsers is experimental, and may not'
                                            ' always import all open tabs.\n\nAlso note that session files are used '
                                            'to read session data, so please ensure that you\'ve waited about half '
                                            'a minute or so before running this.')
        descriptionLabel.setWordWrap(True)
        dialogLayout.addWidget(descriptionLabel, 0, 0, 1, 2)

        firefoxGroup = QtWidgets.QGroupBox('Firefox Options')
        firefoxGroupLayout = QtWidgets.QVBoxLayout()
        firefoxGroup.setLayout(firefoxGroupLayout)
        self.firefoxChoice = QtWidgets.QCheckBox('Get tabs from Firefox')
        self.firefoxChoice.setStyleSheet(Stylesheets.CHECK_BOX_STYLESHEET)
        self.firefoxSessionChoice = QtWidgets.QCheckBox('Get entire session instead of latest tabs')
        self.firefoxSessionChoice.setStyleSheet(Stylesheets.CHECK_BOX_STYLESHEET)
        firefoxGroupLayout.addWidget(self.firefoxChoice)
        firefoxGroupLayout.addWidget(self.firefoxSessionChoice)

        chromeGroup = QtWidgets.QGroupBox('Chrome Options')
        chromeGroupLayout = QtWidgets.QVBoxLayout()
        chromeGroup.setLayout(chromeGroupLayout)
        self.chromeChoice = QtWidgets.QCheckBox('Get tabs from Chrome / Chromium (Experimental)')
        self.chromeChoice.setStyleSheet(Stylesheets.CHECK_BOX_STYLESHEET)
        chromeGroupLayout.addWidget(self.chromeChoice)

        dialogLayout.addWidget(firefoxGroup, 1, 0, 1, 2)
        dialogLayout.addWidget(chromeGroup, 2, 0, 1, 2)

        self.importScreenshotsCheckbox = QtWidgets.QCheckBox('Take screenshots of sites')
        self.importScreenshotsCheckbox.setStyleSheet(Stylesheets.CHECK_BOX_STYLESHEET)
        dialogLayout.addWidget(self.importScreenshotsCheckbox, 3, 0, 1, 2)

        self.importToCanvasCheckbox = QtWidgets.QCheckBox('Import To Canvas:')
        self.importToCanvasCheckbox.setStyleSheet(Stylesheets.CHECK_BOX_STYLESHEET)
        self.importToCanvasDropdown = QtWidgets.QComboBox()
        self.importToCanvasDropdown.addItems(list(parent.parent().centralWidget().tabbedPane.canvasTabs))
        self.importToCanvasDropdown.setEditable(False)
        self.importToCanvasDropdown.setDisabled(True)
        self.importToCanvasCheckbox.toggled.connect(lambda: self.importToCanvasDropdown.setDisabled(
            self.importToCanvasDropdown.isEnabled()))
        dialogLayout.addWidget(self.importToCanvasCheckbox, 4, 0, 1, 1)
        dialogLayout.addWidget(self.importToCanvasDropdown, 4, 1, 1, 1)

        acceptButton = QtWidgets.QPushButton('Accept')
        acceptButton.setAutoDefault(True)
        acceptButton.setDefault(True)
        cancelButton = QtWidgets.QPushButton('Cancel')
        acceptButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)
        acceptButton.setFocus()

        self.setMaximumWidth(450)
        self.setMinimumWidth(450)
        self.setMaximumHeight(400)
        self.setMinimumHeight(400)

        dialogLayout.addWidget(cancelButton, 5, 0, 1, 1)
        dialogLayout.addWidget(acceptButton, 5, 1, 1, 1)


class ServerConnectWizard(QtWidgets.QDialog):
    """
    Dialog Window that lets the user input the details of the server that
    they want to connect to.
    """

    def __init__(self, parent):
        super().__init__(parent=parent)
        self.setLayout(QtWidgets.QFormLayout())
        self.setWindowTitle("Server Connection Wizard")
        # self.setMinimumSize(550,200)

        serverIPLabel = QtWidgets.QLabel("Server IP:")
        self.serverIPTextbox = QtWidgets.QLineEdit()
        self.layout().addRow(serverIPLabel, self.serverIPTextbox)

        serverPortLabel = QtWidgets.QLabel("Server Port:")
        self.serverPortTextbox = QtWidgets.QLineEdit("3777")
        self.layout().addRow(serverPortLabel, self.serverPortTextbox)

        serverPasswordLabel = QtWidgets.QLabel("Server Password:")
        self.serverPasswordTextbox = QtWidgets.QLineEdit()
        self.serverPasswordTextbox.setEchoMode(QtWidgets.QLineEdit.Password)
        self.layout().addRow(serverPasswordLabel, self.serverPasswordTextbox)

        self.confirmConnect = False
        confirmButton = QtWidgets.QPushButton("Confirm")
        cancelButton = QtWidgets.QPushButton("Cancel")
        self.layout().addRow(cancelButton, confirmButton)

        confirmButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)

    def accept(self):
        self.confirmConnect = True
        super().accept()


class ServerCreateOrOpenProject(QtWidgets.QDialog):

    def __init__(self, mainWindow):
        super(ServerCreateOrOpenProject, self).__init__(parent=mainWindow)
        self.setModal(True)

        with mainWindow.serverProjectsLock:
            serverProjects = mainWindow.serverProjects

        self.setLayout(QtWidgets.QVBoxLayout())
        self.openProject = True
        self.projectName = ''
        self.projectPass = ''

        openProjectWidget = QtWidgets.QWidget()
        openProjectLayout = QtWidgets.QFormLayout()
        openProjectWidget.setLayout(openProjectLayout)
        self.openProjectDropdown = QtWidgets.QComboBox()
        self.openProjectDropdown.setToolTip('Select the name of the server project to work on.')
        self.openProjectDropdown.setEditable(False)
        self.openProjectDropdown.addItems(serverProjects)
        self.openProjectPassword = QtWidgets.QLineEdit('')
        self.openProjectPassword.setToolTip('Enter the password of the selected server project.')
        self.openProjectPassword.setEchoMode(QtWidgets.QLineEdit.Password)
        openProjectLayout.addRow('Open Project:', self.openProjectDropdown)
        openProjectLayout.addRow('Password:', self.openProjectPassword)
        openProjectButton = QtWidgets.QPushButton('Open Project')

        self.layout().addWidget(openProjectWidget)
        self.layout().addWidget(openProjectButton)

        createProjectWidget = QtWidgets.QWidget()
        createProjectLayout = QtWidgets.QFormLayout()
        createProjectWidget.setLayout(createProjectLayout)
        self.createProjectNameTextbox = QtWidgets.QLineEdit('')
        self.createProjectNameTextbox.setToolTip('Specify the name of the server project. Must be unique.')
        self.createProjectPasswordTextbox = QtWidgets.QLineEdit('')
        self.createProjectPasswordTextbox.setEchoMode(QtWidgets.QLineEdit.Password)
        self.createProjectPasswordTextbox.setToolTip('Specify a password to be entered'
                                                     ' in order to access this project.')

        createProjectLayout.addRow('Project Name:', self.createProjectNameTextbox)
        createProjectLayout.addRow('Project Password:', self.createProjectPasswordTextbox)
        createProjectButton = QtWidgets.QPushButton('Create Server Project')

        self.layout().addWidget(createProjectWidget)
        self.layout().addWidget(createProjectButton)

        openProjectButton.clicked.connect(self.openExistingProject)
        createProjectButton.clicked.connect(self.createNewProject)

    def createNewProject(self) -> None:
        self.projectName = self.createProjectNameTextbox.text()
        if self.projectName == '':
            self.parent().MESSAGEHANDLER.warning('Project name cannot be blank.', popUp=True)
            return
        self.projectPass = self.createProjectPasswordTextbox.text()
        self.openProject = False
        self.accept()

    def openExistingProject(self) -> None:
        self.projectName = self.openProjectDropdown.currentText()
        if self.projectName == '':
            self.parent().MESSAGEHANDLER.warning('Project name cannot be blank.', popUp=True)
            return
        self.projectPass = self.openProjectPassword.text()
        self.openProject = True
        self.accept()


class ViewAndStopResolutionsDialog(QtWidgets.QDialog):

    def __init__(self, mainWindowObject):
        super(ViewAndStopResolutionsDialog, self).__init__()
        self.setModal(True)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.mainWindowObject = mainWindowObject

        resolutionsLabel = QtWidgets.QLabel('Running Resolutions:')

        resolutionsLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.layout().addWidget(resolutionsLabel)

        scrollArea = QtWidgets.QScrollArea()
        scrollAreaLayout = QtWidgets.QFormLayout()
        scrollArea.setLayout(scrollAreaLayout)

        for resolution in mainWindowObject.resolutions:
            if resolution[1]:
                resolutionName = 'Server Resolution: ' + resolution[0].resolution
                stopResolutionButton = ViewAndStopResolutionsDialogOption(resolution[0],
                                                                          resolution[1], mainWindowObject)
                scrollAreaLayout.addRow(QtWidgets.QLabel(resolutionName), stopResolutionButton)
            elif not resolution[0].done:
                resolutionName = 'Local Resolution: ' + resolution[0].resolution
                stopResolutionButton = ViewAndStopResolutionsDialogOption(resolution[0],
                                                                          resolution[1], mainWindowObject)
                scrollAreaLayout.addRow(QtWidgets.QLabel(resolutionName), stopResolutionButton)

        self.layout().addWidget(scrollArea)
        self.setMinimumWidth(scrollArea.width())
        self.resize(scrollArea.width(), 400)


class ViewAndStopResolutionsDialogOption(QtWidgets.QPushButton):

    def __init__(self, resolutionThread, fromServer, mainWindowObject):
        super(ViewAndStopResolutionsDialogOption, self).__init__()
        self.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)
        self.mainWindowObject = mainWindowObject
        self.resolutionThread = resolutionThread
        self.fromServer = fromServer
        self.setText('Stop Resolution')

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if self.fromServer:
            self.mainWindowObject.FCOM.abortResolution(self.resolutionThread.resolution, self.resolutionThread.uid)
        else:
            self.resolutionThread.return_results = False
            self.resolutionThread.exit()
            self.mainWindowObject.cleanUpLocalFinishedResolutions()
        # Remove from parent's layout
        self.parent().layout().removeRow(self)


class ImportFromFileDialog(QtWidgets.QDialog):
    def popupFileDialog(self):
        self.fileDirectory = QtWidgets.QFileDialog().getOpenFileName(parent=self, caption='Select file to import',
                                                                     options=QtWidgets.QFileDialog.DontUseNativeDialog,
                                                                     filter="CSV or txt (*.csv *.txt)")[0]
        if self.fileDirectory != '':
            self.fileDirectoryLine.setText(self.fileDirectory)

    def __init__(self, parent):
        super(ImportFromFileDialog, self).__init__(parent=parent)
        self.fileDirectory = ''
        self.setWindowTitle('Import From File')
        self.setModal(True)

        dialogLayout = QtWidgets.QGridLayout()
        self.setLayout(dialogLayout)
        descriptionLabel = QtWidgets.QLabel('Choose the filetype you selected')
        descriptionLabel.setWordWrap(True)
        dialogLayout.addWidget(descriptionLabel, 0, 0, 1, 2)

        self.fileDirectoryButton = QtWidgets.QPushButton("Select file...")
        self.fileDirectoryLine = QtWidgets.QLineEdit()
        self.fileDirectoryLine.setReadOnly(True)
        self.textFileChoice = QtWidgets.QRadioButton('Text file')
        self.textFileChoice.setStyleSheet(Stylesheets.RADIO_BUTTON_STYLESHEET)
        self.textFileChoice.setChecked(True)
        self.CSVFileChoice = QtWidgets.QRadioButton('CSV (Please see documentation for formatting)')
        self.CSVFileChoice.setStyleSheet(Stylesheets.RADIO_BUTTON_STYLESHEET)

        dialogLayout.addWidget(self.fileDirectoryLine, 1, 0, 1, 2)
        dialogLayout.addWidget(self.fileDirectoryButton, 2, 0, 1, 2)
        dialogLayout.addWidget(self.textFileChoice, 3, 0, 1, 2)
        dialogLayout.addWidget(self.CSVFileChoice, 4, 0, 1, 2)

        self.importToCanvasCheckbox = QtWidgets.QCheckBox('Import To Canvas:')
        self.importToCanvasCheckbox.setStyleSheet(Stylesheets.CHECK_BOX_STYLESHEET)
        self.importToCanvasDropdown = QtWidgets.QComboBox()
        self.importToCanvasDropdown.addItems(list(parent.parent().centralWidget().tabbedPane.canvasTabs))
        self.importToCanvasDropdown.setEditable(False)
        self.importToCanvasDropdown.setDisabled(True)
        self.importToCanvasCheckbox.toggled.connect(lambda: self.importToCanvasDropdown.setDisabled(
            self.importToCanvasDropdown.isEnabled()))
        dialogLayout.addWidget(self.importToCanvasCheckbox, 5, 0, 1, 1)
        dialogLayout.addWidget(self.importToCanvasDropdown, 5, 1, 1, 1)

        acceptButton = QtWidgets.QPushButton('Accept')
        acceptButton.setAutoDefault(True)
        acceptButton.setDefault(True)
        cancelButton = QtWidgets.QPushButton('Cancel')
        self.fileDirectoryButton.clicked.connect(self.popupFileDialog)
        acceptButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)
        acceptButton.setFocus()

        self.setMaximumWidth(500)
        self.setMinimumWidth(300)
        self.setMaximumHeight(300)
        self.setMinimumHeight(300)

        dialogLayout.addWidget(cancelButton, 6, 0, 1, 1)
        dialogLayout.addWidget(acceptButton, 6, 1, 1, 1)


class ImportFromTextFileDialog(QtWidgets.QDialog):

    def __init__(self, parent):
        super(ImportFromTextFileDialog, self).__init__(parent=parent)
        self.setWindowTitle('Import From Text File')
        self.setModal(True)

        dialogLayout = QtWidgets.QGridLayout()
        self.setLayout(dialogLayout)
        descriptionLabel = QtWidgets.QLabel('Choose what type the entities will be imported as')
        descriptionLabel.setWordWrap(True)
        dialogLayout.addWidget(descriptionLabel, 0, 0, 1, 2)

        self.importTypeDropdown = QtWidgets.QComboBox()
        self.importTypeDropdown.addItems(parent.parent().RESOURCEHANDLER.getAllEntities())
        self.importTypeDropdown.setEditable(False)

        dialogLayout.addWidget(self.importTypeDropdown, 3, 1, 1, 1)

        acceptButton = QtWidgets.QPushButton('Accept')
        acceptButton.setAutoDefault(True)
        acceptButton.setDefault(True)
        cancelButton = QtWidgets.QPushButton('Cancel')
        acceptButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)
        acceptButton.setFocus()

        self.setMaximumWidth(450)
        self.setMinimumWidth(300)
        self.setMaximumHeight(300)
        self.setMinimumHeight(300)

        dialogLayout.addWidget(cancelButton, 4, 0, 1, 1)
        dialogLayout.addWidget(acceptButton, 4, 1, 1, 1)


class CanvasPictureDialog(QtWidgets.QDialog):

    def __init__(self, parent):
        super(CanvasPictureDialog, self).__init__(parent=parent)
        self.fileDirectory = ""
        self.setWindowTitle('Save Canvas Picture')
        self.setModal(True)

        dialogLayout = QtWidgets.QGridLayout()
        self.setLayout(dialogLayout)
        descriptionLabel = QtWidgets.QLabel('Choose the directory to save the Picture to:')
        descriptionLabel.setWordWrap(True)
        dialogLayout.addWidget(descriptionLabel, 0, 0, 1, 2)

        self.fileDirectoryButton = QtWidgets.QPushButton("Select directory...")
        self.fileDirectoryLine = QtWidgets.QLineEdit()
        self.fileDirectoryLine.setReadOnly(True)
        self.transparentChoice = QtWidgets.QRadioButton('Transparent')
        self.transparentChoice.setChecked(True)
        self.withBackgroundChoice = QtWidgets.QRadioButton('With Background')

        dialogLayout.addWidget(self.fileDirectoryLine, 1, 0, 1, 2)
        dialogLayout.addWidget(self.fileDirectoryButton, 2, 0, 1, 2)
        dialogLayout.addWidget(self.transparentChoice, 3, 0, 1, 1)
        dialogLayout.addWidget(self.withBackgroundChoice, 3, 1, 1, 1)

        canvasLabel = QtWidgets.QLabel('Canvas:')
        canvasLabel.setWordWrap(False)
        dialogLayout.addWidget(canvasLabel, 5, 0, 1, 1)
        self.chosenCanvasDropdown = QtWidgets.QComboBox()
        self.chosenCanvasDropdown.addItems(list(parent.parent().centralWidget().tabbedPane.canvasTabs))
        self.chosenCanvasDropdown.setEditable(False)
        dialogLayout.addWidget(self.chosenCanvasDropdown, 5, 1, 1, 1)

        acceptButton = QtWidgets.QPushButton('Accept')
        acceptButton.setAutoDefault(True)
        acceptButton.setDefault(True)
        acceptButton.setFocus()
        cancelButton = QtWidgets.QPushButton('Cancel')
        self.fileDirectoryButton.clicked.connect(self.popupFileDialog)
        acceptButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)

        self.setMaximumWidth(500)
        self.setMinimumWidth(300)
        self.setMaximumHeight(300)
        self.setMinimumHeight(300)

        dialogLayout.addWidget(cancelButton, 6, 0, 1, 1)
        dialogLayout.addWidget(acceptButton, 6, 1, 1, 1)

    def popupFileDialog(self):
        saveAsDialog = QtWidgets.QFileDialog()
        saveAsDialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
        saveAsDialog.setViewMode(QtWidgets.QFileDialog.List)
        saveAsDialog.setNameFilter("Image (*.png)")
        saveAsDialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        saveAsDialog.exec()
        self.fileDirectory = saveAsDialog.selectedFiles()[0]
        if self.fileDirectory != '':
            if Path(self.fileDirectory).suffix != 'png':
                self.fileDirectory = str(Path(self.fileDirectory).with_suffix('.png'))
            self.fileDirectoryLine.setText(self.fileDirectory)
