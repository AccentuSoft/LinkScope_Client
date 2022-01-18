#!/usr/bin/env python3


import hashlib
import re
import json
import platform
import sqlite3
import tempfile
import shutil
import os
import time

import magic
import lz4.block
import pandas as pd
import webbrowser
from typing import Union
from urllib import parse
from pathlib import Path
from datetime import datetime
from uuid import uuid4

from playwright.sync_api import sync_playwright, Error, TimeoutError

from PySide6 import QtWidgets, QtGui, QtCore
from Core.Interface import Stylesheets
from Core.Interface.Entity import BaseNode


class MenuBar(QtWidgets.QMenuBar):

    def __init__(self, parent):
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

        graphMLCanvasAction = QtGui.QAction("From GraphML - Canvas",
                                            self,
                                            statusTip="Import canvas from a GraphML file.",
                                            triggered=self.parent().importCanvasFromGraphML)

        graphMLDatabaseAction = QtGui.QAction("From GraphML - Database",
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
        GraphMLCanvas = QtGui.QAction('To GraphML - Canvas ',
                                      self,
                                      statusTip="Export Canvas to GraphML",
                                      triggered=self.parent().exportCanvasToGraphML)

        GraphMLDatabase = QtGui.QAction('To GraphML - Database ',
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

        findAction = QtGui.QAction("&Find",
                                   self,
                                   statusTip="Find Links or Entities by their Primary Field",
                                   triggered=self.findEntityOrLink)
        findAction.setShortcut("Ctrl+F")
        viewMenu.addAction(findAction)

        typeFindAction = QtGui.QAction("Find Entity of Type",
                                       self,
                                       statusTip="Find Entities of a certain type by their Primary Field",
                                       triggered=self.findEntitiesOfType)
        viewMenu.addAction(typeFindAction)

        regexFindAction = QtGui.QAction("Regex Find",
                                        self,
                                        statusTip="Find Links or Entities by their Primary Field using Regex",
                                        triggered=self.findEntityOrLinkRegex)
        viewMenu.addAction(regexFindAction)

        regexTypeFindAction = QtGui.QAction("Regex Find Entity of Type",
                                            self,
                                            statusTip="Find Entities of a certain type by their Primary Field using "
                                                      "Regex",
                                            triggered=self.findEntitiesOfTypeRegex)
        viewMenu.addAction(regexTypeFindAction)
        viewMenu.addSeparator()

        runningResolutionsAction = QtGui.QAction("&Running Resolutions",
                                                 self,
                                                 statusTip="View Running Resolutions",
                                                 triggered=self.runningResolutions)
        runningResolutionsAction.setShortcut("Ctrl+R")
        viewMenu.addAction(runningResolutionsAction)
        viewMenu.addSeparator()
        openWebsiteInBrowserTabAction = QtGui.QAction("Open Selected Websites in Browser",
                                                      self,
                                                      statusTip="Open the Selected Website entities in new "
                                                                "Browser tabs.",
                                                      triggered=self.openWebsite)
        viewMenu.addAction(openWebsiteInBrowserTabAction)
        viewMenu.addSeparator()

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
        newNodes = []
        newLinks = []
        fileDirectory = Path(importDialog.fileDirectoryLine.text())
        if importDialogAccept and fileDirectory != '':
            if fileDirectory.exists() and fileDirectory.is_file():
                sceneToAddTo = None

                try:
                    if importDialog.textFileChoice.isChecked():
                        fileContents = []
                        with open(fileDirectory, 'r') as importFile:
                            # Read a maximum of 3 lines from the file:
                            count = 0
                            for line in importFile:
                                fileContents.append(line.strip())
                                count += 1
                                if count >= 3:
                                    break

                        importTextFileDialog = ImportFromTextFileDialog(self, fileContents)
                        if importTextFileDialog.exec_():
                            if importTextFileDialog.importToCanvasCheckbox.isChecked():
                                sceneToAddTo = self.parent().centralWidget().tabbedPane.getSceneByName(
                                    importTextFileDialog.importToCanvasDropdown.currentText())

                            selectedEntityType = importTextFileDialog.importTypeDropdown.currentText()
                            primary_field = importTextFileDialog.typePrimaryFieldValueLabel.text()

                            with open(fileDirectory, 'r') as importFile:
                                for line in importFile:
                                    lineValue = line.strip()
                                    if lineValue:
                                        newEntityJSON = {primary_field: lineValue.strip(),
                                                         'Entity Type': selectedEntityType}
                                        if newEntityJSON not in newNodes:
                                            newNodes.append(newEntityJSON)
                    elif importDialog.CSVFileChoice.isChecked():
                        csvDF = pd.read_csv(fileDirectory)

                        # Remove duplicate column names
                        csvDF = csvDF.loc[:, ~csvDF.columns.duplicated()]

                        # Fill NaN values with an empty string
                        csvDF.fillna('')

                        # If we have less than 2 rows, we cannot import
                        rowNumber = len(csvDF.index)
                        if rowNumber < 2:
                            raise ValueError("Invalid CSV file data - Not enough rows.")

                        if len(csvDF.columns) < 1:
                            raise ValueError("Invalid CSV file data - Not enough columns.")

                        importEntityCSVDialog = ImportEntityFromCSVFile(self, csvDF)
                        if importEntityCSVDialog.exec_():
                            attributeRows = [comboBox.currentText()
                                             for comboBox in importEntityCSVDialog.fieldMappingComboBoxes]
                            for attribute in range(len(attributeRows)):
                                if attributeRows[attribute] == '':
                                    attributeRows[attribute] = csvDF.columns[attribute]

                            if importEntityCSVDialog.importToCanvasCheckbox.isChecked():
                                sceneToAddTo = self.parent().centralWidget().tabbedPane.getSceneByName(
                                    importEntityCSVDialog.importToCanvasDropdown.currentText())

                            entityTypeToImportAs = importEntityCSVDialog.entityTypeChoiceDropdown.currentText()
                            for row in csvDF.itertuples(index=False):
                                newEntityJSON = {str(attributeRows[key]).strip(): str(row[key]).strip()
                                                 for key in range(len(attributeRows))}
                                newEntityJSON['Entity Type'] = entityTypeToImportAs
                                if newEntityJSON not in newNodes:
                                    newNodes.append(newEntityJSON)

                    elif importDialog.CSVFileChoiceLinks.isChecked():
                        csvDF = pd.read_csv(fileDirectory)

                        # Remove duplicate column names
                        csvDF = csvDF.loc[:, ~csvDF.columns.duplicated()]

                        # Fill NaN values with an empty string
                        csvDF.fillna('')

                        # If we have less than 2 rows, we cannot import
                        rowNumber = len(csvDF.index)
                        if rowNumber < 2:
                            raise ValueError("Invalid CSV file data - Not enough rows.")

                        if len(csvDF.columns) < 1:
                            raise ValueError("Invalid CSV file data - Not enough columns.")

                        importLinksCSVDialog = ImportLinksFromCSVFile(self, csvDF)
                        if importLinksCSVDialog.exec_():
                            unmapped = []
                            for columnIndex in range(len(importLinksCSVDialog.fieldMappingComboBoxes)):
                                columnMapping = importLinksCSVDialog.fieldMappingComboBoxes[columnIndex].currentText()
                                if columnMapping != '':
                                    csvDF.rename(columns={csvDF.columns[columnIndex]: columnMapping}, inplace=True)
                                elif not importLinksCSVDialog.fieldIncludeCheckBoxes[columnIndex].isChecked():
                                    unmapped.append(csvDF.columns[columnIndex])

                            if unmapped:
                                fieldsRemainingDF = csvDF[unmapped].copy()
                                for unmappedField in unmapped:
                                    csvDF.drop(unmappedField, axis=1, inplace=True)
                                createLinkEntitiesDialog = ImportLinkEntitiesFromCSVFile(self, fieldsRemainingDF)

                                if createLinkEntitiesDialog.exec_():
                                    entityOneType = importLinksCSVDialog.entityOneTypeChoiceDropdown.currentText()
                                    entityTwoType = importLinksCSVDialog.entityTwoTypeChoiceDropdown.currentText()

                                    attributeRows = [comboBox.currentText()
                                                     for comboBox in createLinkEntitiesDialog.fieldMappingComboBoxes]
                                    for attribute in range(len(attributeRows)):
                                        if attributeRows[attribute] == '':
                                            attributeRows[attribute] = fieldsRemainingDF.columns[attribute]

                                    entityTypeToImportAs = \
                                        createLinkEntitiesDialog.entityTypeChoiceDropdown.currentText()

                                    newEntityPrimaryAttribute = \
                                        self.parent().RESOURCEHANDLER.getPrimaryFieldForEntityType(entityTypeToImportAs)

                                    for entityRow, linkRow in zip(fieldsRemainingDF.itertuples(index=False),
                                                                  csvDF.itertuples(index=False)):

                                        count = 0
                                        linkJSON = {}
                                        entityOneJSON = {}
                                        entityTwoJSON = {}
                                        resolutionID = ""
                                        notes = ""

                                        for column in linkRow:
                                            column = str(column)
                                            mapping = csvDF.columns[count]
                                            if mapping == 'Entity One':
                                                entityOneJSON = self.parent().LENTDB.getEntityOfType(column,
                                                                                                     entityOneType)
                                            elif mapping == 'Entity Two':
                                                entityTwoJSON = self.parent().LENTDB.getEntityOfType(column,
                                                                                                     entityTwoType)
                                            elif mapping == 'Notes':
                                                notes = column
                                            elif mapping == 'Resolution ID':
                                                resolutionID = column
                                            else:
                                                linkJSON[mapping] = column
                                            count += 1

                                        if (entityOneJSON is not None) and (entityTwoJSON is not None):
                                            # linkJSON['uid'] = (entityOneJSON['uid'], entityTwoJSON['uid'])
                                            linkJSON['Notes'] = notes
                                            if importLinksCSVDialog.randAsIs.isChecked():
                                                linkJSON['Resolution'] = resolutionID
                                            elif importLinksCSVDialog.randMerge.isChecked():
                                                linkJSON['Resolution'] = resolutionID + ' | ' + str(uuid4())
                                            elif importLinksCSVDialog.randReplace.isChecked():
                                                linkJSON['Resolution'] = str(uuid4())

                                            # If 'Resolution ID' is not mapped, generate random IDs.
                                            if not linkJSON.get('Resolution'):
                                                linkJSON['Resolution'] = str(uuid4())

                                            linkJSONOne = dict(linkJSON)
                                            linkJSONOne['Resolution'] += ' OUT'
                                            linkJSONTwo = dict(linkJSON)
                                            linkJSONTwo['Resolution'] += ' IN'
                                            linkJSONThree = dict(linkJSON)

                                            newEntityJSON = {str(attributeRows[key]): str(entityRow[key]).strip()
                                                             for key in range(len(attributeRows))}
                                            newEntityJSON['Entity Type'] = entityTypeToImportAs
                                            newNode = self.parent().LENTDB.getEntityOfType(
                                                newEntityJSON[newEntityPrimaryAttribute], entityTypeToImportAs)
                                            if not newNode:
                                                newNode = self.parent().LENTDB.addEntity(newEntityJSON,
                                                                                         updateTimeline=False)

                                            linkJSONOne['uid'] = (entityOneJSON['uid'], newNode['uid'])
                                            linkJSONTwo['uid'] = (newNode['uid'], entityTwoJSON['uid'])
                                            linkJSONThree['uid'] = (entityOneJSON['uid'], entityTwoJSON['uid'])
                                            self.parent().LENTDB.addLink(linkJSONOne)
                                            self.parent().LENTDB.addLink(linkJSONTwo)
                                            self.parent().LENTDB.addLink(linkJSONThree)

                                            newLinks.append((entityOneJSON['uid'], newNode['uid'],
                                                             linkJSONOne['Resolution']))
                                            newLinks.append((newNode['uid'], entityTwoJSON['uid'],
                                                             linkJSONTwo['Resolution']))
                                            newLinks.append((entityOneJSON['uid'], entityTwoJSON['uid'],
                                                             linkJSONThree['Resolution']))

                            else:
                                entityOneType = importLinksCSVDialog.entityOneTypeChoiceDropdown.currentText()
                                entityTwoType = importLinksCSVDialog.entityTwoTypeChoiceDropdown.currentText()

                                for row in csvDF.itertuples(index=False):
                                    count = 0
                                    linkJSON = {}
                                    entityOneJSON = {}
                                    entityTwoJSON = {}
                                    resolutionID = ""
                                    notes = ""

                                    for column in row:
                                        column = str(column)
                                        mapping = csvDF.columns[count]
                                        if mapping == 'Entity One':
                                            entityOneJSON = self.parent().LENTDB.getEntityOfType(column, entityOneType)
                                        elif mapping == 'Entity Two':
                                            entityTwoJSON = self.parent().LENTDB.getEntityOfType(column, entityTwoType)
                                        elif mapping == 'Notes':
                                            notes = column
                                        elif mapping == 'Resolution ID':
                                            resolutionID = column
                                        else:
                                            linkJSON[mapping] = column
                                        count += 1

                                    if (entityOneJSON is not None) and (entityTwoJSON is not None):
                                        linkJSON['uid'] = (entityOneJSON['uid'], entityTwoJSON['uid'])
                                        linkJSON['Notes'] = notes
                                        if importLinksCSVDialog.randAsIs.isChecked():
                                            linkJSON['Resolution'] = resolutionID
                                        elif importLinksCSVDialog.randMerge.isChecked():
                                            linkJSON['Resolution'] = resolutionID + ' | ' + str(uuid4())
                                        elif importLinksCSVDialog.randReplace.isChecked():
                                            linkJSON['Resolution'] = str(uuid4())

                                        # If 'Resolution ID' is not mapped, generate random IDs.
                                        if not linkJSON.get('Resolution'):
                                            linkJSON['Resolution'] = str(uuid4())

                                        self.parent().LENTDB.addLink(linkJSON)
                                        newLinks.append((entityOneJSON['uid'], entityTwoJSON['uid'],
                                                         linkJSON['Resolution']))

                    newNodeUIDs = [newEntity['uid'] for newEntity in self.parent().LENTDB.addEntities(newNodes)]

                    if sceneToAddTo is not None:
                        for newNodeUID in newNodeUIDs:
                            if newNodeUID is not None:
                                sceneToAddTo.addNodeProgrammatic(newNodeUID)
                        sceneToAddTo.rearrangeGraph()

                    if newLinks:
                        self.parent().centralWidget().tabbedPane.addLinksToTabs(newLinks, 'File Links',
                                                                                linkGroupingOverride=True)
                        self.parent().LENTDB.resetTimeline()

                except PermissionError:
                    self.parent().MESSAGEHANDLER.error('No permission to access the file at the path provided.',
                                                       popUp=True, exc_info=False)
                except UnicodeDecodeError:
                    self.parent().MESSAGEHANDLER.error('File path provided points to a binary file that cannot be '
                                                       'interpreted as text.', popUp=True, exc_info=False)
                except FileNotFoundError:
                    self.parent().MESSAGEHANDLER.error('File path provided does not point to an existing file.',
                                                       popUp=True, exc_info=False)
                except TypeError:
                    self.parent().MESSAGEHANDLER.error('Type Error occurred while processing file. Please ensure that '
                                                       'you have selected a file of the appropriate type.',
                                                       popUp=True, exc_info=False)
                except Exception as e:
                    self.parent().MESSAGEHANDLER.error('Exception occurred while processing file: ' + str(e),
                                                       popUp=True, exc_info=False)
            else:
                self.parent().MESSAGEHANDLER.error('Invalid file path provided!', popUp=True, exc_info=False)

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

    def findEntityOrLinkRegex(self) -> None:
        self.parent().findEntityOrLinkOnCanvas(regex=True)

    def findEntitiesOfType(self) -> None:
        self.parent().findEntityOfTypeOnCanvas()

    def findEntitiesOfTypeRegex(self) -> None:
        self.parent().findEntityOfTypeOnCanvas(regex=True)

    def openWebsite(self) -> None:
        currentScene = self.parent().centralWidget().tabbedPane.getCurrentScene()
        for item in currentScene.selectedItems():
            if isinstance(item, BaseNode):
                itemJSON = self.parent().LENTDB.getEntity(item.uid)
                if itemJSON.get('Entity Type') == 'Website':
                    try:
                        webbrowser.open(itemJSON['URL'], new=0, autoraise=True)
                    except KeyError:
                        continue

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

                            cookiesDatabasePath = tabsFilePath.parent.parent / 'cookies.sqlite'
                            newCookiesDatabase = tempfile.mkstemp(suffix='.sqlite')
                            newCookiesDatabasePath = Path(newCookiesDatabase[1])

                            # Try to copy the database a few times, so we can access it
                            #   with sqlite (original is locked)
                            copiedFile = False
                            for _ in range(5):
                                shutil.copyfile(cookiesDatabasePath, newCookiesDatabasePath)
                                originalDigest = self.cookieFileHashHelper(cookiesDatabasePath)
                                newDigest = self.cookieFileHashHelper(newCookiesDatabasePath)
                                if originalDigest == newDigest:
                                    copiedFile = True
                                    break
                                else:
                                    time.sleep(0.2)

                            browserCookies = []
                            if not copiedFile:
                                self.parent().MESSAGEHANDLER.warning('Could not access Firefox cookies.', popUp=True)
                            else:
                                cookiesDB = sqlite3.connect(newCookiesDatabasePath)
                                for cookie in cookiesDB.execute('SELECT name,value,host,path,expiry,isSecure,'
                                                                'isHttpOnly,sameSite FROM moz_cookies'):
                                    newCookie = {'name': cookie[0], 'value': cookie[1],
                                                 'domain': cookie[2], 'path': cookie[3],
                                                 'expires': cookie[4], 'secure': bool(cookie[5]),
                                                 'httpOnly': bool(cookie[6])}
                                    if cookie[7] == 0:
                                        newCookie['sameSite'] = "None"
                                    elif cookie[7] == 1:
                                        newCookie['sameSite'] = "Lax"
                                    elif cookie[7] == 2:
                                        newCookie['sameSite'] = "Strict"
                                    browserCookies.append(newCookie)
                                cookiesDB.close()
                            newCookiesDatabasePath.unlink(missing_ok=True)
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
                                        # If we time out, take a screenshot of the page as-is.
                                        try:
                                            page.goto(actualURL)
                                        except TimeoutError:
                                            pass

                                        urlSaveDir = projectFilesDir / urlTitle

                                        try:
                                            if not urlSaveDir.exists():
                                                urlSaveDir.mkdir(mode=0o700)
                                        except OSError:
                                            urlSaveDir = None

                                        if urlSaveDir is not None:
                                            timeNow = str(datetime.now().timestamp() * 1000000).split('.')[0]
                                            screenshotSavePath = str(urlSaveDir / (
                                                    actualURL.replace('/', '+') + ' ' + timeNow + ' screenshot.png'))
                                            page.screenshot(path=screenshotSavePath, full_page=True)

                                            returnResults.append(
                                                [{'Image Name': decodedPath + ' Screenshot ' + timeNow,
                                                  'File Path': screenshotSavePath,
                                                  'Entity Type': 'Image'},
                                                 {len(returnResults) - 1: {'Resolution': 'Screenshot of Tab',
                                                                           'Notes': ''}}])

                        browser.close()
                    except Error as e:
                        self.parent().MESSAGEHANDLER.warning('Cannot import tabs from Firefox: ' + str(repr(e)),
                                                             popUp=True)

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
                            sessionFilePath = Path.home() / 'AppData' / 'Local' / 'Google' / 'Chrome' / 'User Data' / \
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
                            WARNING: This is a hackish solution that does not always work. Documentation and tools to
                                     work with chrome and chromium session files are lacking last I checked,
                                     and most of the existing ones have been broken since the last update.
                                     This is a best-effort solution for now, which should mostly work.
            
                                     As for how it works, it's just pattern matching after some observations about the
                                     file structure of chrome session files.
            
                                     This will probably be revised in the future to make it actually parse chrome
                                     session files.
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
                                        # If we time out, take a screenshot of the page as-is.
                                        try:
                                            page.goto(tabURL)
                                        except TimeoutError:
                                            pass
                                        urlSaveDir = projectFilesDir / urlTitle

                                        try:
                                            if not urlSaveDir.exists():
                                                urlSaveDir.mkdir(mode=0o700)
                                        except OSError:
                                            urlSaveDir = None

                                        if urlSaveDir is not None:
                                            timeNow = str(datetime.now().timestamp() * 1000000).split('.')[0]
                                            screenshotSavePath = str(urlSaveDir / (
                                                    tabURL.replace('/', '+') + ' ' + timeNow + ' screenshot.png'))
                                            page.screenshot(path=screenshotSavePath, full_page=True)

                                            returnResults.append(
                                                [{'Image Name': decodedPath + ' Screenshot ' + timeNow,
                                                  'File Path': screenshotSavePath,
                                                  'Entity Type': 'Image'},
                                                 {len(returnResults) - 1: {'Resolution': 'Screenshot of Tab',
                                                                           'Notes': ''}}])

                        browser.close()
                    except Error:
                        self.parent().MESSAGEHANDLER.warning('Chrome / Chromium executable is not installed. Cannot '
                                                             'import tabs from Chrome / Chromium.', popUp=True)

            progress.setValue(3)
            if progress.wasCanceled():
                progress.setValue(4)
                self.parent().setStatus('Cancelled importing entities from Browser.')
                return
            if returnResults:
                self.importBrowserTabsFindings(returnResults, importDialog.importToCanvasCheckbox.isChecked(),
                                               importDialog.importToCanvasDropdown.currentText())
            progress.setValue(4)

    def cookieFileHashHelper(self, filePath):
        cookieHash = hashlib.md5()  # nosec
        with open(filePath, 'rb') as cookieFile:
            for chunk in iter(lambda: cookieFile.read(4096), b""):
                cookieHash.update(chunk)
        return cookieHash.digest()

    def importBrowserTabsFindings(self, resolution_result: list, importToCanvas: Union[bool, None] = None,
                                  canvasToImportTo: Union[str, None] = None) -> None:
        # See the function 'facilitateResolution' in CentralPane for guidance.

        # Get all the entities, then split it into several lists, to make searching & iterating through them faster.
        allEntities = [(entity['uid'], (entity[list(entity)[1]], entity['Entity Type']))
                       for entity in self.parent().LENTDB.getAllEntities()]
        if allEntities:
            allEntityUIDs, allEntityPrimaryFieldsAndTypes = map(list, zip(*allEntities))
        else:
            allEntityUIDs = []
            allEntityPrimaryFieldsAndTypes = []
        allLinks = [linkUID['uid'] for linkUID in self.parent().LENTDB.getAllLinks()]
        links = []
        newNodeUIDs = []
        for resultList in resolution_result:
            newNodeJSON = resultList[0]
            newNodeEntityType = newNodeJSON['Entity Type']
            # Cannot assume proper order of dicts sent over the net.
            newNodePrimaryFieldKey = self.parent().RESOURCEHANDLER.getPrimaryFieldForEntityType(newNodeEntityType)
            newNodePrimaryField = newNodeJSON[newNodePrimaryFieldKey]

            try:
                # Attempt to get the index of an existing entity that shares primary field and type with the new
                #   entity. Those two entities are considered to be referring to the same thing.
                newNodeExistsIndex = allEntityPrimaryFieldsAndTypes.index((newNodePrimaryField, newNodeEntityType))
                # If entity already exists, update the fields and re-add
                newNodeExistingUID = allEntityUIDs[newNodeExistsIndex]
                existingEntityJSON = self.parent().LENTDB.getEntity(newNodeExistingUID)
                # Remove primary field and entity type, since those are duplicates. Primary field is the first element.
                del newNodeJSON['Entity Type']
                del newNodeJSON[newNodePrimaryFieldKey]
                try:
                    notesField = newNodeJSON.pop('Notes')
                    existingEntityJSON['Notes'] += '\n' + notesField
                except KeyError:
                    # If no new field was actually added to the entity, don't re-add to the database
                    if len(newNodeJSON) == 0:
                        newNodeUIDs.append(newNodeExistingUID)
                        continue
                # Update old values to new ones, and add new ones where applicable.
                existingEntityJSON.update(dict((newNodeKey, newNodeJSON[newNodeKey]) for newNodeKey in newNodeJSON))
                self.parent().LENTDB.addEntity(existingEntityJSON, fromServer=True, updateTimeline=False)
                newNodeUIDs.append(newNodeExistingUID)
            except ValueError:
                # If there is no index for which the primary field and entity type of the new node match one of the
                #   existing ones, the node must indeed be new. We add it here.
                entityJson = self.parent().LENTDB.addEntity(newNodeJSON, fromServer=True, updateTimeline=False)
                newNodeUIDs.append(entityJson['uid'])
                # Ensure that different entities involved in the resolution can't independently
                #   create the same new entities.
                allEntityUIDs.append(entityJson['uid'])
                allEntityPrimaryFieldsAndTypes.append((newNodePrimaryField, newNodeEntityType))

        for resultListIndex in range(len(resolution_result)):
            if len(resolution_result[resultListIndex]) > 1:
                outputEntityUID = newNodeUIDs[resultListIndex]
                parentsDict = resolution_result[resultListIndex][1]
                for parentID in parentsDict:
                    parentUID = parentID
                    if isinstance(parentUID, int):
                        parentUID = newNodeUIDs[parentUID]
                    resolutionName = parentsDict[parentID]['Resolution']
                    newLinkUID = (parentUID, outputEntityUID)
                    # Avoid creating more links between the same two entities.
                    if newLinkUID in allLinks:
                        linkJson = self.parent().LENTDB.getLinkIfExists(newLinkUID)
                        if resolutionName not in linkJson['Notes']:
                            linkJson['Notes'] += '\nConnection also produced by Resolution: ' + resolutionName
                            self.parent().LENTDB.addLink(linkJson, fromServer=True)
                    else:
                        self.parent().LENTDB.addLink({'uid': newLinkUID, 'Resolution': resolutionName,
                                                      'Notes': parentsDict[parentID]['Notes']}, fromServer=True)
                        links.append((parentUID, outputEntityUID, resolutionName))
                        allLinks.append(newLinkUID)

        self.parent().syncDatabase()
        if importToCanvas:
            sceneToAddTo = self.parent().centralWidget().tabbedPane.getSceneByName(canvasToImportTo)
            for newNodeUID in newNodeUIDs:
                if newNodeUID is not None and newNodeUID not in sceneToAddTo.sceneGraph.nodes:
                    sceneToAddTo.addNodeProgrammatic(newNodeUID)
            sceneToAddTo.rearrangeGraph()
        self.parent().centralWidget().tabbedPane.addLinksToTabs(links, "Browser Import")
        self.parent().LENTDB.resetTimeline()
        self.parent().saveProject()
        self.parent().MESSAGEHANDLER.info('Imported tabs from browser successfully.')


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
        self.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)
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


class ImportLinksFromCSVFile(QtWidgets.QDialog):

    def __init__(self, parent, csvTableContents: pd.DataFrame):
        super(ImportLinksFromCSVFile, self).__init__(parent=parent)

        self.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)
        self.setModal(True)
        importLayout = QtWidgets.QVBoxLayout()
        self.setLayout(importLayout)
        self.setWindowTitle("Import Links from CSV")

        columnNumber = len(csvTableContents.columns)

        titleLabel = QtWidgets.QLabel("Import Links from CSV")
        titleLabel.setAlignment(QtCore.Qt.AlignCenter)

        descLabel = QtWidgets.QLabel("Select the Entity Type of the Parent entity (Entity One) and the Entity Type of "
                                     "the Child entity (Entity Two). Then, map these entities to columns in the CSV "
                                     "file. You may also map the rest of the fields to the other columns of the CSV "
                                     "file. Lastly, choose how to import and / or generate the ID for each Resolution.")
        descLabel.setWordWrap(True)

        entityOneTypeChoiceWidget = QtWidgets.QWidget()
        entityOneTypeChoiceLayout = QtWidgets.QHBoxLayout()
        entityOneTypeChoiceWidget.setLayout(entityOneTypeChoiceLayout)
        entityOneTypeChoiceLabel = QtWidgets.QLabel("Entity One type:")
        self.entityOneTypeChoiceDropdown = QtWidgets.QComboBox()
        self.entityOneTypeChoiceDropdown.setEditable(False)
        self.entityOneTypeChoiceDropdown.addItems(parent.parent().RESOURCEHANDLER.getAllEntities())
        entityOneTypeChoiceLayout.addWidget(entityOneTypeChoiceLabel)
        entityOneTypeChoiceLayout.addWidget(self.entityOneTypeChoiceDropdown)

        entityTwoTypeChoiceWidget = QtWidgets.QWidget()
        entityTwoTypeChoiceLayout = QtWidgets.QHBoxLayout()
        entityTwoTypeChoiceWidget.setLayout(entityTwoTypeChoiceLayout)
        entityTwoTypeChoiceLabel = QtWidgets.QLabel("Entity Two type:")
        self.entityTwoTypeChoiceDropdown = QtWidgets.QComboBox()
        self.entityTwoTypeChoiceDropdown.setEditable(False)
        self.entityTwoTypeChoiceDropdown.addItems(parent.parent().RESOURCEHANDLER.getAllEntities())
        entityTwoTypeChoiceLayout.addWidget(entityTwoTypeChoiceLabel)
        entityTwoTypeChoiceLayout.addWidget(self.entityTwoTypeChoiceDropdown)

        self.fieldIncludeCheckBoxes = []
        tableFieldCheckBoxesWidget = QtWidgets.QWidget()
        tableFieldCheckBoxesWidgetLayout = QtWidgets.QHBoxLayout()
        tableFieldCheckBoxesWidget.setLayout(tableFieldCheckBoxesWidgetLayout)
        for fieldIndex in range(columnNumber):
            checkBoxWidget = QtWidgets.QCheckBox('Include Field? ')
            checkBoxWidget.setToolTip('Check the box to include this column as an attribute for the resolution.')
            self.fieldIncludeCheckBoxes.append(checkBoxWidget)
            tableFieldCheckBoxesWidgetLayout.addWidget(checkBoxWidget)

        self.fieldMappingComboBoxes = []
        tableFieldAttributeMapping = QtWidgets.QWidget()
        tableFieldAttributeMappingLayout = QtWidgets.QHBoxLayout()
        tableFieldAttributeMapping.setLayout(tableFieldAttributeMappingLayout)
        for fieldIndex in range(columnNumber):
            fieldMappingWidget = QtWidgets.QComboBox()
            fieldMappingWidget.setEditable(False)
            fieldMappingWidget.currentIndexChanged.connect(self.changeMappingForField)
            fieldMappingWidget.addItems(['', 'Entity One', 'Entity Two', 'Resolution ID', 'Notes'])
            self.fieldMappingComboBoxes.append(fieldMappingWidget)
            tableFieldAttributeMappingLayout.addWidget(fieldMappingWidget)

        csvTable = QtWidgets.QTableWidget(3, columnNumber, self)
        csvTable.setHorizontalHeaderLabels(csvTableContents.columns)
        for row in csvTableContents[:3].itertuples():
            rowValues = list(row)
            for column in range(columnNumber):
                columnItem = QtWidgets.QTableWidgetItem(str(rowValues[column + 1]))
                columnItem.setFlags(columnItem.flags() & ~QtCore.Qt.ItemIsEditable)
                csvTable.setItem(rowValues[0], column, columnItem)

        randomizationLabel = QtWidgets.QLabel("If the resolution identifiers (i.e. 'Resolution ID') are not guaranteed "
                                              "to be unique, you can configure whether you'd like to leave them as-is, "
                                              "append a random token, or ignore any resolution identifiers and just "
                                              "have random tokens as the Resolution IDs.\nPlease select what you would "
                                              "like to do:")
        randomizationLabel.setWordWrap(True)
        randomizationLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.randAsIs = QtWidgets.QRadioButton("Use 'Resolution ID' as-is.")
        self.randMerge = QtWidgets.QRadioButton("Append a random token to the values mapped to the 'Resolution ID' "
                                                "field.")
        self.randReplace = QtWidgets.QRadioButton("Ignore the 'Resolution ID' mapping, instead generate random values "
                                                  "for Resolution IDs.")
        self.randAsIs.setChecked(True)

        buttonsWidget = QtWidgets.QWidget()
        buttonsWidgetLayout = QtWidgets.QHBoxLayout()
        buttonsWidget.setLayout(buttonsWidgetLayout)
        confirmButton = QtWidgets.QPushButton('Confirm')
        cancelButton = QtWidgets.QPushButton('Cancel')
        buttonsWidgetLayout.addWidget(cancelButton)
        buttonsWidgetLayout.addWidget(confirmButton)
        cancelButton.clicked.connect(self.reject)
        confirmButton.clicked.connect(self.checkIfEntitiesAreMapped)

        importLayout.addWidget(titleLabel)
        importLayout.addWidget(descLabel)
        importLayout.addWidget(entityOneTypeChoiceWidget)
        importLayout.addWidget(entityTwoTypeChoiceWidget)
        importLayout.addWidget(tableFieldAttributeMapping)
        importLayout.addWidget(csvTable)
        importLayout.addWidget(tableFieldCheckBoxesWidget)
        importLayout.addWidget(randomizationLabel)
        importLayout.addWidget(self.randAsIs)
        importLayout.addWidget(self.randMerge)
        importLayout.addWidget(self.randReplace)
        importLayout.addWidget(buttonsWidget)

    def changeMappingForField(self, newIndex):
        for comboBoxIndex in range(len(self.fieldMappingComboBoxes)):
            comboBox = self.fieldMappingComboBoxes[comboBoxIndex]
            checkBox = self.fieldIncludeCheckBoxes[comboBoxIndex]
            if comboBox.currentIndex() == newIndex:
                if newIndex == 0:
                    checkBox.setEnabled(True)
                else:
                    if comboBox.hasFocus():
                        checkBox.setEnabled(False)
                        checkBox.setChecked(True)
                    else:
                        comboBox.setCurrentIndex(0)
                        if newIndex != 0:
                            checkBox.setEnabled(True)
                            checkBox.setChecked(False)

    def checkIfEntitiesAreMapped(self):
        # Check if Entity One and Entity Two labels are assigned, do not proceed if not.
        isOneAssigned = False
        isTwoAssigned = False
        for comboBox in self.fieldMappingComboBoxes:
            if comboBox.currentIndex() == 1:
                isOneAssigned = True
            elif comboBox.currentIndex() == 2:
                isTwoAssigned = True
        if isOneAssigned and isTwoAssigned:
            self.accept()
        else:
            self.parent().parent().MESSAGEHANDLER.warning('Need to at least configure mappings for Entity One (parent) '
                                                          'and Entity Two (child) before proceeding.', popUp=True)


class ImportLinkEntitiesFromCSVFile(QtWidgets.QDialog):

    def __init__(self, parent, csvTableContents: pd.DataFrame):
        super(ImportLinkEntitiesFromCSVFile, self).__init__(parent=parent)

        self.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)
        self.setModal(True)
        importLayout = QtWidgets.QVBoxLayout()
        self.setLayout(importLayout)
        self.setWindowTitle("Create Entities from Link Fields")

        columnNumber = len(csvTableContents.columns)

        titleLabel = QtWidgets.QLabel("Create Entities from Link Fields")
        titleLabel.setAlignment(QtCore.Qt.AlignCenter)

        descLabel = QtWidgets.QLabel("Select the entity type to import the remaining fields as. "
                                     "Then, configure the mapping between the CSV fields and entity attributes. To do "
                                     "so, select from the drop-down boxes the entity attributes that correspond to "
                                     "each field in the CSV file. The drop-down boxes left blank will have the "
                                     "corresponding CSV column names be treated as attribute names for the new "
                                     "entities.")
        descLabel.setWordWrap(True)

        entityTypeChoiceWidget = QtWidgets.QWidget()
        entityTypeChoiceLayout = QtWidgets.QHBoxLayout()
        entityTypeChoiceWidget.setLayout(entityTypeChoiceLayout)

        entityTypeChoiceLabel = QtWidgets.QLabel("Entity Type to Import As:")
        self.entityTypeChoiceDropdown = QtWidgets.QComboBox()
        self.entityTypeChoiceDropdown.setEditable(False)
        self.entityTypeChoiceDropdown.addItems(parent.parent().RESOURCEHANDLER.getAllEntities())
        self.entityTypeChoiceDropdown.currentIndexChanged.connect(self.pickEntityToImportAs)
        entityTypeChoiceLayout.addWidget(entityTypeChoiceLabel)
        entityTypeChoiceLayout.addWidget(self.entityTypeChoiceDropdown)

        self.fieldMappingComboBoxes = []
        tableFieldAttributeMapping = QtWidgets.QWidget()
        tableFieldAttributeMappingLayout = QtWidgets.QHBoxLayout()
        tableFieldAttributeMapping.setLayout(tableFieldAttributeMappingLayout)
        for fieldIndex in range(columnNumber):
            fieldMappingWidget = QtWidgets.QComboBox()
            fieldMappingWidget.setEditable(False)
            fieldMappingWidget.currentIndexChanged.connect(self.changeMappingForField)
            fieldMappingWidget.addItem('')
            self.fieldMappingComboBoxes.append(fieldMappingWidget)
            tableFieldAttributeMappingLayout.addWidget(fieldMappingWidget)

        csvTable = QtWidgets.QTableWidget(3, columnNumber, self)
        csvTable.setHorizontalHeaderLabels(csvTableContents.columns)
        for row in csvTableContents[:3].itertuples():
            rowValues = list(row)
            for column in range(columnNumber):
                columnItem = QtWidgets.QTableWidgetItem(str(rowValues[column + 1]))
                columnItem.setFlags(columnItem.flags() & ~QtCore.Qt.ItemIsEditable)
                csvTable.setItem(rowValues[0], column, columnItem)

        buttonsWidget = QtWidgets.QWidget()
        buttonsWidgetLayout = QtWidgets.QHBoxLayout()
        buttonsWidget.setLayout(buttonsWidgetLayout)
        confirmButton = QtWidgets.QPushButton('Confirm')
        cancelButton = QtWidgets.QPushButton('Cancel')
        buttonsWidgetLayout.addWidget(cancelButton)
        buttonsWidgetLayout.addWidget(confirmButton)
        cancelButton.clicked.connect(self.reject)
        confirmButton.clicked.connect(self.confirmThatPrimaryFieldIsMapped)

        importLayout.addWidget(titleLabel)
        importLayout.addWidget(descLabel)
        importLayout.addWidget(entityTypeChoiceWidget)
        importLayout.addWidget(tableFieldAttributeMapping)
        importLayout.addWidget(csvTable)
        importLayout.addWidget(buttonsWidget)

        self.pickEntityToImportAs()

    def pickEntityToImportAs(self):
        currentEntityAttributes = [''] + self.parent().parent().RESOURCEHANDLER.getEntityAttributes(
            self.entityTypeChoiceDropdown.currentText())
        for comboBox in self.fieldMappingComboBoxes:
            comboBox.clear()
            comboBox.addItems(currentEntityAttributes)

    def changeMappingForField(self, newIndex):
        for comboBox in self.fieldMappingComboBoxes:
            if comboBox.currentIndex() == newIndex and not comboBox.hasFocus():
                comboBox.setCurrentIndex(0)

    def confirmThatPrimaryFieldIsMapped(self):
        primaryField = self.parent().parent().RESOURCEHANDLER.getPrimaryFieldForEntityType(
            self.entityTypeChoiceDropdown.currentText())
        for comboBox in self.fieldMappingComboBoxes:
            if comboBox.currentText() == primaryField:
                self.accept()
        self.parent().parent().MESSAGEHANDLER.warning('Primary field (' + primaryField +
                                                      ') needs to be mapped before proceeding.')


class ImportEntityFromCSVFile(QtWidgets.QDialog):

    def __init__(self, parent, csvTableContents: pd.DataFrame):
        super(ImportEntityFromCSVFile, self).__init__(parent=parent)

        self.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)
        self.setModal(True)
        importLayout = QtWidgets.QVBoxLayout()
        self.setLayout(importLayout)
        self.setWindowTitle("Import Entities from CSV")

        columnNumber = len(csvTableContents.columns)

        titleLabel = QtWidgets.QLabel("Import Entities from CSV")
        titleLabel.setAlignment(QtCore.Qt.AlignCenter)

        descLabel = QtWidgets.QLabel("Select the entity type to import the entities from the CSV file as. "
                                     "Then, configure the mapping between the CSV fields and entity attributes. To do "
                                     "so, select from the drop-down boxes the entity attributes that correspond to "
                                     "each field in the CSV file. The drop-down boxes left blank will have the "
                                     "corresponding CSV column names be treated as attribute names for the new "
                                     "entities.")
        descLabel.setWordWrap(True)

        entityTypeChoiceWidget = QtWidgets.QWidget()
        entityTypeChoiceLayout = QtWidgets.QHBoxLayout()
        entityTypeChoiceWidget.setLayout(entityTypeChoiceLayout)

        entityTypeChoiceLabel = QtWidgets.QLabel("Entity Type to Import As:")
        self.entityTypeChoiceDropdown = QtWidgets.QComboBox()
        self.entityTypeChoiceDropdown.setEditable(False)
        self.entityTypeChoiceDropdown.addItems(parent.parent().RESOURCEHANDLER.getAllEntities())
        self.entityTypeChoiceDropdown.currentIndexChanged.connect(self.pickEntityToImportAs)
        entityTypeChoiceLayout.addWidget(entityTypeChoiceLabel)
        entityTypeChoiceLayout.addWidget(self.entityTypeChoiceDropdown)

        self.fieldMappingComboBoxes = []
        tableFieldAttributeMapping = QtWidgets.QWidget()
        tableFieldAttributeMappingLayout = QtWidgets.QHBoxLayout()
        tableFieldAttributeMapping.setLayout(tableFieldAttributeMappingLayout)
        for fieldIndex in range(columnNumber):
            fieldMappingWidget = QtWidgets.QComboBox()
            fieldMappingWidget.setEditable(False)
            fieldMappingWidget.currentIndexChanged.connect(self.changeMappingForField)
            fieldMappingWidget.addItem('')
            self.fieldMappingComboBoxes.append(fieldMappingWidget)
            tableFieldAttributeMappingLayout.addWidget(fieldMappingWidget)

        csvTable = QtWidgets.QTableWidget(3, columnNumber, self)
        csvTable.setHorizontalHeaderLabels(csvTableContents.columns)
        for row in csvTableContents[:3].itertuples():
            rowValues = list(row)
            for column in range(columnNumber):
                columnItem = QtWidgets.QTableWidgetItem(str(rowValues[column + 1]))
                columnItem.setFlags(columnItem.flags() & ~QtCore.Qt.ItemIsEditable)
                csvTable.setItem(rowValues[0], column, columnItem)

        importToCanvasChoiceWidget = QtWidgets.QWidget()
        importToCanvasChoiceLayout = QtWidgets.QHBoxLayout()
        importToCanvasChoiceWidget.setLayout(importToCanvasChoiceLayout)
        self.importToCanvasCheckbox = QtWidgets.QCheckBox('Import To Canvas:')
        self.importToCanvasCheckbox.setStyleSheet(Stylesheets.CHECK_BOX_STYLESHEET)
        self.importToCanvasDropdown = QtWidgets.QComboBox()
        self.importToCanvasDropdown.addItems(list(parent.parent().centralWidget().tabbedPane.canvasTabs))
        self.importToCanvasDropdown.setEditable(False)
        self.importToCanvasDropdown.setDisabled(True)
        self.importToCanvasCheckbox.toggled.connect(lambda: self.importToCanvasDropdown.setDisabled(
            self.importToCanvasDropdown.isEnabled()))
        importToCanvasChoiceLayout.addWidget(self.importToCanvasCheckbox)
        importToCanvasChoiceLayout.addWidget(self.importToCanvasDropdown)

        buttonsWidget = QtWidgets.QWidget()
        buttonsWidgetLayout = QtWidgets.QHBoxLayout()
        buttonsWidget.setLayout(buttonsWidgetLayout)
        confirmButton = QtWidgets.QPushButton('Confirm')
        cancelButton = QtWidgets.QPushButton('Cancel')
        buttonsWidgetLayout.addWidget(cancelButton)
        buttonsWidgetLayout.addWidget(confirmButton)
        cancelButton.clicked.connect(self.reject)
        confirmButton.clicked.connect(self.confirmThatPrimaryFieldIsMapped)

        importLayout.addWidget(titleLabel)
        importLayout.addWidget(descLabel)
        importLayout.addWidget(entityTypeChoiceWidget)
        importLayout.addWidget(tableFieldAttributeMapping)
        importLayout.addWidget(csvTable)
        importLayout.addWidget(importToCanvasChoiceWidget)
        importLayout.addWidget(buttonsWidget)

        self.pickEntityToImportAs()

    def pickEntityToImportAs(self):
        currentEntityAttributes = [''] + self.parent().parent().RESOURCEHANDLER.getEntityAttributes(
            self.entityTypeChoiceDropdown.currentText())
        for comboBox in self.fieldMappingComboBoxes:
            comboBox.clear()
            comboBox.addItems(currentEntityAttributes)

    def changeMappingForField(self, newIndex):
        for comboBox in self.fieldMappingComboBoxes:
            if comboBox.currentIndex() == newIndex and not comboBox.hasFocus():
                comboBox.setCurrentIndex(0)

    def confirmThatPrimaryFieldIsMapped(self):
        primaryField = self.parent().parent().RESOURCEHANDLER.getPrimaryFieldForEntityType(
            self.entityTypeChoiceDropdown.currentText())
        primaryFieldMapped = False
        for comboBox in self.fieldMappingComboBoxes:
            if comboBox.currentText() == primaryField:
                # Executing self.accept() will not actually end the prompt, so we use bools to check and confirm.
                primaryFieldMapped = True
                break
        if primaryFieldMapped:
            self.accept()
        else:
            self.parent().parent().MESSAGEHANDLER.warning('Primary field (' + primaryField +
                                                          ') needs to be mapped before proceeding.')


class ImportFromFileDialog(QtWidgets.QDialog):
    def popupFileDialog(self):
        self.fileDirectory = QtWidgets.QFileDialog().getOpenFileName(parent=self, caption='Select File to Import From',
                                                                     dir=str(Path.home()),
                                                                     options=QtWidgets.QFileDialog.DontUseNativeDialog,
                                                                     filter="CSV or txt (*.csv *.txt)")[0]
        if self.fileDirectory != '':
            self.fileDirectoryLine.setText(self.fileDirectory)

    def __init__(self, parent):
        super(ImportFromFileDialog, self).__init__(parent=parent)
        self.fileDirectory = ''
        self.setWindowTitle('Import Entities From File')
        self.setModal(True)

        dialogLayout = QtWidgets.QGridLayout()
        self.setLayout(dialogLayout)
        descriptionLabel = QtWidgets.QLabel('Select the file to import Entities or Links from:')
        descriptionLabel.setAlignment(QtCore.Qt.AlignCenter)
        descriptionLabel.setWordWrap(True)
        dialogLayout.addWidget(descriptionLabel, 0, 0, 1, 2)

        self.fileDirectoryButton = QtWidgets.QPushButton("Select file...")
        self.fileDirectoryLine = QtWidgets.QLineEdit()
        self.fileDirectoryLine.setReadOnly(True)

        fileChoiceLabel = QtWidgets.QLabel('Specify the type of the chosen file and what to import:')
        fileChoiceLabel.setAlignment(QtCore.Qt.AlignCenter)
        fileChoiceLabel.setWordWrap(True)

        self.textFileChoice = QtWidgets.QRadioButton('Text file - Entities Import')
        self.textFileChoice.setStyleSheet(Stylesheets.RADIO_BUTTON_STYLESHEET)
        self.textFileChoice.setChecked(True)
        self.CSVFileChoice = QtWidgets.QRadioButton('CSV - Entities Import')
        self.CSVFileChoice.setStyleSheet(Stylesheets.RADIO_BUTTON_STYLESHEET)
        self.CSVFileChoiceLinks = QtWidgets.QRadioButton('CSV - Links Import')
        self.CSVFileChoiceLinks.setStyleSheet(Stylesheets.RADIO_BUTTON_STYLESHEET)

        dialogLayout.addWidget(self.fileDirectoryLine, 1, 0, 1, 2)
        dialogLayout.addWidget(self.fileDirectoryButton, 2, 0, 1, 2)
        dialogLayout.addWidget(fileChoiceLabel, 3, 0, 1, 2)
        dialogLayout.addWidget(self.textFileChoice, 4, 0, 1, 2)
        dialogLayout.addWidget(self.CSVFileChoice, 5, 0, 1, 2)
        dialogLayout.addWidget(self.CSVFileChoiceLinks, 6, 0, 1, 2)

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

        dialogLayout.addWidget(cancelButton, 7, 0, 1, 1)
        dialogLayout.addWidget(acceptButton, 7, 1, 1, 1)


class ImportFromTextFileDialog(QtWidgets.QDialog):

    def __init__(self, parent, fileContents):
        super(ImportFromTextFileDialog, self).__init__(parent=parent)
        self.setWindowTitle('Import From Text File')
        self.setModal(True)

        dialogLayout = QtWidgets.QGridLayout()
        self.setLayout(dialogLayout)
        descriptionLabel = QtWidgets.QLabel('Importing entities from text file, one entity per line.')
        descriptionLabel.setAlignment(QtCore.Qt.AlignCenter)
        descriptionLabel.setWordWrap(True)
        dialogLayout.addWidget(descriptionLabel, 0, 0, 1, 2)

        importTypeLabel = QtWidgets.QLabel('Choose the Entity Type to import as:')
        importTypeLabel.setWordWrap(True)
        dialogLayout.addWidget(importTypeLabel, 1, 0, 1, 1)

        self.importTypeDropdown = QtWidgets.QComboBox()
        self.importTypeDropdown.addItems(parent.parent().RESOURCEHANDLER.getAllEntities())
        self.importTypeDropdown.setEditable(False)
        dialogLayout.addWidget(self.importTypeDropdown, 1, 1, 1, 1)
        self.importTypeDropdown.currentTextChanged.connect(self.updatePrimaryFieldValueLabel)

        typePrimaryFieldLabel = QtWidgets.QLabel('Primary Field for chosen type:')
        typePrimaryFieldLabel.setWordWrap(False)
        dialogLayout.addWidget(typePrimaryFieldLabel, 2, 0, 1, 1)

        self.typePrimaryFieldValueLabel = QtWidgets.QLineEdit('')
        self.typePrimaryFieldValueLabel.setReadOnly(True)
        dialogLayout.addWidget(self.typePrimaryFieldValueLabel, 2, 1, 1, 1)

        textTable = QtWidgets.QTableWidget(3, 1, self)
        textTable.setWordWrap(True)
        textTable.setFixedWidth(450)
        for line in range(len(fileContents)):
            columnItem = QtWidgets.QTableWidgetItem(fileContents[line])
            columnItem.setFlags(columnItem.flags() & ~QtCore.Qt.ItemIsEditable)
            textTable.setItem(line, 0, columnItem)
        textTable.setColumnWidth(0, 450)
        textTable.setHorizontalHeaderLabels(['File Entities Preview'])

        dialogLayout.addWidget(textTable, 3, 0, 1, 2)

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

        self.setFixedWidth(472)
        self.setFixedHeight(300)

        dialogLayout.addWidget(cancelButton, 5, 0, 1, 1)
        dialogLayout.addWidget(acceptButton, 5, 1, 1, 1)

        # Initialize the primary field value label to whatever is the primary field of the first entity
        #   in the drop down selection box.
        self.updatePrimaryFieldValueLabel()

    def updatePrimaryFieldValueLabel(self):
        self.typePrimaryFieldValueLabel.setText(str(self.parent().parent().RESOURCEHANDLER.getPrimaryFieldForEntityType(
            self.importTypeDropdown.currentText())))


class CanvasPictureDialog(QtWidgets.QDialog):

    def __init__(self, parent):
        super(CanvasPictureDialog, self).__init__(parent=parent)
        self.fileDirectory = ""
        self.setWindowTitle('Save Canvas Picture')
        self.setModal(True)
        self.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)

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
