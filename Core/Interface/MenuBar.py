#!/usr/bin/env python3


import contextlib
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
import tldextract

from typing import Union
from urllib import parse
from pathlib import Path
from datetime import datetime
from uuid import uuid4

from playwright.sync_api import sync_playwright, Error, TimeoutError

from PySide6 import QtWidgets, QtGui, QtCore
from Core.GlobalVariables import user_agents
from Core.Interface.Entity import BaseNode
from Core.ResourceHandler import StringPropertyInput, FilePropertyInput, SingleChoicePropertyInput, \
    MultiChoicePropertyInput, resizePictureFromBuffer


class MenuBar(QtWidgets.QMenuBar):
    browserTabsImportDoneSignalListener = QtCore.Signal(list, str)

    def __init__(self, parent):
        super().__init__(parent=parent)

        self.browserTabsImportDoneSignalListener.connect(self.importBrowserTabsFindings)

        fileMenu = self.addMenu("File")

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

        openProjectFilesAction = QtGui.QAction("Browse Project Files",
                                     self,
                                     statusTip="Open the Project Files directory for this project.",
                                     triggered=self.openProjectFilesDir)
        fileMenu.addAction(openProjectFilesAction)

        checkForUpdateAction = QtGui.QAction("Check for Updates",
                                     self,
                                     statusTip="Check if there are any updates for LinkScope available.",
                                     triggered=self.checkForUpdates)
        fileMenu.addAction(checkForUpdateAction)

        importMenu = self.addMenu("Import")

        fromBrowserAction = QtGui.QAction("From Browser",
                                          self,
                                          statusTip="Import open tabs as Website and materials entities.",
                                          triggered=self.importFromBrowser)

        fromTorBrowserAction = QtGui.QAction("From TOR Browser",
                                             self,
                                             statusTip="Import open TOR tabs as Website and materials entities.",
                                             triggered=self.importFromTORBrowser)

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
        importMenu.addAction(fromTorBrowserAction)
        importMenu.addAction(fromFileAction)
        importMenu.addAction(graphMLCanvasAction)
        importMenu.addAction(graphMLDatabaseAction)

        exportMenu = self.addMenu("Export")

        canvasPictureAction = QtGui.QAction("Save Picture of Canvas", self,
                                            statusTip="Save a picture of your canvas",
                                            triggered=self.savePic)
        GraphMLCanvas = QtGui.QAction('To GraphML - Canvas',
                                      self,
                                      statusTip="Export Canvas to GraphML",
                                      triggered=self.parent().exportCanvasToGraphML)

        GraphMLDatabase = QtGui.QAction('To GraphML - Database',
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

        editResolution = QtGui.QAction('Resolutions Settings',
                                       self,
                                       statusTip="Edit Resolutions Settings",
                                       triggered=self.editResolutionsSettings)

        editProject = QtGui.QAction('Project Settings',
                                    self,
                                    statusTip="Edit Project Settings",
                                    triggered=self.editProjectSettings)

        editProgram = QtGui.QAction('Program Settings',
                                    self,
                                    statusTip="Edit Program Settings",
                                    triggered=self.editProgramSettings)

        editGraphics = QtGui.QAction('Graphics Settings',
                                     self,
                                     statusTip="Edit Graphics Settings",
                                     triggered=self.editGraphicsSettings)

        editSettingsMenu.addAction(editLog)
        editSettingsMenu.addAction(editResolution)
        editSettingsMenu.addAction(editProject)
        editSettingsMenu.addAction(editProgram)
        editSettingsMenu.addAction(editGraphics)

        exitAction = QtGui.QAction("Exit",
                                   self,
                                   statusTip="Save, Close Project and Exit",
                                   triggered=self.exitSoftware)
        fileMenu.addAction(exitAction)

        viewMenu = self.addMenu("View")

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
        regexFindAction.setShortcut("Ctrl+Shift+F")

        regexTypeFindAction = QtGui.QAction("Regex Find Entity of Type",
                                            self,
                                            statusTip="Find Entities of a certain type by their Primary Field using "
                                                      "Regex",
                                            triggered=self.findEntitiesOfTypeRegex)
        viewMenu.addAction(regexTypeFindAction)
        viewMenu.addSeparator()

        resolutionFindAction = QtGui.QAction("Find &Resolutions",
                                             self,
                                             statusTip="Find Resolutions based on a set of parameters",
                                             triggered=self.findResolutions)
        resolutionFindAction.setShortcut("Ctrl+R")
        viewMenu.addAction(resolutionFindAction)

        runningResolutionsAction = QtGui.QAction("View Running Resolutions",
                                                 self,
                                                 statusTip="View Running Resolutions",
                                                 triggered=self.runningResolutions)
        viewMenu.addAction(runningResolutionsAction)
        viewMenu.addSeparator()

        rearrangeGraphAction = QtGui.QAction("Rearrange Canvas Graph",
                                             self,
                                             statusTip="Rearrange the nodes on the current Canvas to a default "
                                                       "configuration according to the currently configured graphing "
                                                       "algorithm.",
                                             triggered=self.rearrangeGraph)
        viewMenu.addAction(rearrangeGraphAction)

        rearrangeAsTimelineAction = QtGui.QAction("Rearrange Canvas Graph as Timeline",
                                                  self,
                                                  statusTip="Rearrange the nodes on the current Canvas to a "
                                                            "Left-to-Right half-tree according to the entities' "
                                                            "creation date.",
                                                  triggered=self.rearrangeGraphToTimeLine)
        viewMenu.addAction(rearrangeAsTimelineAction)
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

        nodeOperationsMenu = self.addMenu("Node Operations")

        actionSelectAllNodes = QtGui.QAction('Select All Nodes',
                                             self,
                                             statusTip="Select all nodes on this canvas.",
                                             triggered=self.selectAllNodes)
        actionSelectAllNodes.setShortcut('Ctrl+A')
        nodeOperationsMenu.addAction(actionSelectAllNodes)

        actionSelectChildren = QtGui.QAction('Select Child Nodes',
                                             self,
                                             statusTip="Select the child entities of the selected nodes.",
                                             triggered=self.selectChildNodes)
        actionSelectChildren.setShortcut('Ctrl+Shift+C')
        nodeOperationsMenu.addAction(actionSelectChildren)

        actionExpandSelectChildren = QtGui.QAction('Include Child Nodes in Selection',
                                                   self,
                                                   statusTip="Include the child entities of the selected nodes "
                                                             "in the current selection.",
                                                   triggered=self.selectExpandChildNodes)
        actionExpandSelectChildren.setShortcut('Ctrl+Alt+C')
        nodeOperationsMenu.addAction(actionExpandSelectChildren)

        actionSelectParents = QtGui.QAction('Select Parent Nodes',
                                            self,
                                            statusTip="Select the parent entities of the selected nodes.",
                                            triggered=self.selectParentNodes)
        actionSelectParents.setShortcut('Ctrl+Shift+P')
        nodeOperationsMenu.addAction(actionSelectParents)

        actionExpandSelectParents = QtGui.QAction('Include Parent Nodes in Selection',
                                                  self,
                                                  statusTip="Include the parent entities of the selected nodes "
                                                            "in the current selection.",
                                                  triggered=self.selectExpandParentNodes)
        actionExpandSelectParents.setShortcut('Ctrl+Alt+P')
        nodeOperationsMenu.addAction(actionExpandSelectParents)

        nodeOperationsMenu.addSeparator()

        actionMacrosWizard = QtGui.QAction('Macros...',
                                           self,
                                           statusTip="View, manage and run Macros.",
                                           triggered=self.viewMacrosWizard)
        actionMacrosWizard.setShortcut('Ctrl+M')
        nodeOperationsMenu.addAction(actionMacrosWizard)

        nodeOperationsMenu.addSeparator()

        downloadWebsitesAction = QtGui.QAction("Download Selected Websites",
                                               self,
                                               statusTip="Download a full copy of the websites pointed to by the URLs "
                                                         "of the selected 'Website' nodes.",
                                               triggered=self.downloadWebsites)
        nodeOperationsMenu.addAction(downloadWebsitesAction)

        screenshotWebsitesAction = QtGui.QAction("Screenshot Selected Websites",
                                                 self,
                                                 statusTip="Take a screenshot of the websites pointed to by the URLs "
                                                           "of the selected 'Website' nodes.",
                                                 triggered=self.screenshotWebsites)
        nodeOperationsMenu.addAction(screenshotWebsitesAction)

        nodeOperationsMenu.addSeparator()

        openWebsiteInBrowserTabAction = QtGui.QAction("Open Selected Websites in Browser",
                                                      self,
                                                      statusTip="Open the Selected Website entities in new "
                                                                "Browser tabs.",
                                                      triggered=self.openWebsite)
        nodeOperationsMenu.addAction(openWebsiteInBrowserTabAction)
        openWebsiteInBrowserTabAction.setShortcut("Ctrl+W")

        openURLInBrowserTabAction = QtGui.QAction("Open Contents of URL Attributes in Browser",
                                                  self,
                                                  statusTip="Open new browser tabs for each valid URL value in all "
                                                            "attributes of all selected entities that contain the "
                                                            "string 'URL' (case insensitive).",
                                                  triggered=self.openURLs)
        nodeOperationsMenu.addAction(openURLInBrowserTabAction)
        openURLInBrowserTabAction.setShortcut("Ctrl+Shift+W")

        nodeOperationsMenu.addSeparator()

        searchOnlineAction = QtGui.QAction("Search Engine Query for Selected Entities",
                                           self,
                                           statusTip="Open Browser tabs running search engine queries on a variety of "
                                                     "search engines for the primary fields of the selected entities.",
                                           triggered=self.searchOnline)
        nodeOperationsMenu.addAction(searchOnlineAction)

        searchImageOnlineAction = QtGui.QAction("Open Image Reverse Search Engines in Browser",
                                                self,
                                                statusTip="Open Browser tabs running image search engines. This is a "
                                                          "helper function to save time, it does not search "
                                                          "automatically.",
                                                triggered=self.searchImageOnline)
        nodeOperationsMenu.addAction(searchImageOnlineAction)

        nodeOperationsMenu.addSeparator()

        notesToTextFilesAction = QtGui.QAction("Save Notes Fields to Text Files",
                                               self,
                                               statusTip="Save the 'Notes' fields of the selected nodes as text files.",
                                               triggered=self.entityNotesToTextFile)
        nodeOperationsMenu.addAction(notesToTextFilesAction)

        nodeOperationsMenu.addSeparator()

        detectCyclesAction = QtGui.QAction("Extract Cycles",
                                           self,
                                           statusTip="Discover cycles in the graph that include the selected nodes, "
                                                     "and extract them to different canvases.",
                                           triggered=self.extractCycles)
        nodeOperationsMenu.addAction(detectCyclesAction)

        projectMenu = self.addMenu("Project Operations")
        generateReportAction = QtGui.QAction("Generate Report",
                                             self,
                                             statusTip="Generate a report from the set of currently selected nodes.",
                                             triggered=self.generateReport)
        projectMenu.addAction(generateReportAction)

        queryAction = QtGui.QAction("Query Wizard",
                                    self,
                                    statusTip="Run LQL Queries.",
                                    triggered=self.queryWizard)
        projectMenu.addAction(queryAction)

        modulesMenu = self.addMenu("Modules")

        reloadModulesAction = QtGui.QAction("Reload Modules", self,
                                            statusTip="Reload all Entities and Transforms from Modules",
                                            triggered=self.reloadModules)
        modulesMenu.addAction(reloadModulesAction)

        viewModuleSourcesAction = QtGui.QAction("View Sources", self,
                                                statusTip="Show the Module Sources Manager",
                                                triggered=self.viewModuleSources)
        modulesMenu.addAction(viewModuleSourcesAction)

        viewModuleManagerAction = QtGui.QAction("View Module Manager", self,
                                                statusTip="Show the Modules Manager",
                                                triggered=self.viewModuleManager)
        modulesMenu.addAction(viewModuleManagerAction)

        serverMenu = self.addMenu("&Server")

        connectAction = QtGui.QAction("Connect", self,
                                      statusTip="Connect to a Server",
                                      triggered=self.serverConnectionWizard)
        serverMenu.addAction(connectAction)

        disconnectAction = QtGui.QAction("Disconnect", self,
                                         statusTip="Disconnect from any connected server",
                                         triggered=self.disconnectFromServer)
        serverMenu.addAction(disconnectAction)

        serverMenu.addSeparator()

        createOrOpenProjectAction = QtGui.QAction("Create or Open Project", self,
                                                  statusTip="Create or Open a new Server project.",
                                                  triggered=self.serverOpenOrCreateProject)
        serverMenu.addAction(createOrOpenProjectAction)

        closeCurrentProjectAction = QtGui.QAction("Close Current Project", self,
                                                  statusTip="Close the Server project that is currently open.",
                                                  triggered=self.serverCloseProject)
        serverMenu.addAction(closeCurrentProjectAction)

        deleteProjectAction = QtGui.QAction("Delete Current Project", self,
                                            statusTip="Delete the Server project that is currently opened.",
                                            triggered=self.serverDeleteProject)
        serverMenu.addAction(deleteProjectAction)

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
                                          statusTip="Upload selected Materials entity files to Server.",
                                          triggered=self.uploadFiles)
        serverMenu.addAction(uploadFilesAction)

        downloadFilesAction = QtGui.QAction("Download Files", self,
                                            statusTip="Download files from the Server that correspond to the selected "
                                                      "Materials entities.",
                                            triggered=self.downloadFiles)
        serverMenu.addAction(downloadFilesAction)

        serverMenu.addSeparator()

        manageCollectorsAction = QtGui.QAction("Manage Collectors", self,
                                               statusTip="Start and / or stop Collectors for this project.",
                                               triggered=self.manageCollectors)
        serverMenu.addAction(manageCollectorsAction)

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
            if fileDirectory.is_file():
                sceneToAddTo = None

                try:
                    if importDialog.textFileChoice.isChecked():
                        fileContents = []
                        with open(fileDirectory, 'r') as importFile:
                            # Read a maximum of 3 lines from the file:
                            for index, line in enumerate(importFile):
                                fileContents.append(line.strip())
                                if index > 2:
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
                                        primaryAttr = lineValue.strip()
                                        newEntityJSON = {primary_field: primaryAttr,
                                                         'Entity Type': selectedEntityType}
                                        if newEntityJSON not in newNodes:
                                            existingEntity = self.parent().LENTDB.getEntityOfType(primaryAttr,
                                                                                                  selectedEntityType)
                                            if existingEntity is None:
                                                newNodes.append(newEntityJSON)
                                            else:
                                                existingEntity.update(newEntityJSON)
                                                # We'll refresh the timeline later.
                                                self.parent().LENTDB.addEntity(existingEntity, updateTimeline=False)

                    elif importDialog.CSVFileChoice.isChecked():
                        try:
                            csvDF = pd.read_excel(fileDirectory)
                        except ValueError:
                            csvDF = pd.read_csv(fileDirectory)

                        # If we have no rows or columns, we cannot import anything.
                        # This is essentially a sanity check.
                        if len(csvDF.index) < 1:
                            raise ValueError("Invalid import file data - Not enough rows.")
                        if len(csvDF.columns) < 1:
                            raise ValueError("Invalid import file data - Not enough columns.")

                        # Remove duplicate column names
                        # When importing, all columns should be given unique values,
                        #   so this should be just another sanity check.
                        csvDF = csvDF.loc[:, ~csvDF.columns.duplicated()]

                        # Fill NaN values with an empty string
                        csvDF.fillna('')

                        importEntityCSVDialog = ImportEntityFromCSVFile(self, csvDF)
                        if importEntityCSVDialog.exec_():
                            attributeRows = [comboBox.currentText() or csvDF.columns[index]
                                             for index, comboBox in
                                             enumerate(importEntityCSVDialog.fieldMappingComboBoxes)]

                            if importEntityCSVDialog.importToCanvasCheckbox.isChecked():
                                sceneToAddTo = self.parent().centralWidget().tabbedPane.getSceneByName(
                                    importEntityCSVDialog.importToCanvasDropdown.currentText())

                            entityTypeToImportAs = importEntityCSVDialog.entityTypeChoiceDropdown.currentText()
                            for row in csvDF.itertuples(index=False):
                                newEntityJSON = {str(value).strip(): str(row[index]).strip()
                                                 for index, value in enumerate(attributeRows)}
                                newEntityJSON['Entity Type'] = entityTypeToImportAs
                                if newEntityJSON not in newNodes:
                                    primaryAttr = newEntityJSON[
                                        self.parent().RESOURCEHANDLER.getPrimaryFieldForEntityType(
                                            entityTypeToImportAs)]
                                    existingEntity = self.parent().LENTDB.getEntityOfType(
                                        primaryAttr, entityTypeToImportAs)
                                    if existingEntity is None:
                                        newNodes.append(newEntityJSON)
                                    else:
                                        existingEntity.update(newEntityJSON)
                                        # We'll refresh the timeline later.
                                        self.parent().LENTDB.addEntity(existingEntity, updateTimeline=False)

                    elif importDialog.CSVFileChoiceLinks.isChecked():
                        try:
                            csvDF = pd.read_excel(fileDirectory)
                        except ValueError:
                            csvDF = pd.read_csv(fileDirectory)

                        # If we have no rows or columns, we cannot import anything.
                        # This is essentially a sanity check.
                        if len(csvDF.index) < 1:
                            raise ValueError("Invalid import file data - Not enough rows.")
                        if len(csvDF.columns) < 1:
                            raise ValueError("Invalid import file data - Not enough columns.")

                        # Remove duplicate column names
                        # When importing, all columns should be given unique values,
                        #   so this should be just another sanity check.
                        csvDF = csvDF.loc[:, ~csvDF.columns.duplicated()]

                        # Fill NaN values with an empty string
                        csvDF.fillna('')

                        importLinksCSVDialog = ImportLinksFromCSVFile(self, csvDF)
                        if importLinksCSVDialog.exec_():
                            unmapped = []
                            for columnIndex, columnValue in enumerate(importLinksCSVDialog.fieldMappingComboBoxes):
                                columnMapping = columnValue.currentText()
                                if columnMapping:
                                    csvDF.rename(columns={csvDF.columns[columnIndex]: columnMapping}, inplace=True)
                                elif not importLinksCSVDialog.fieldIncludeCheckBoxes[columnIndex].isChecked():
                                    unmapped.append(csvDF.columns[columnIndex])

                            if unmapped:
                                fieldsRemainingDF = csvDF[unmapped].copy()
                                for unmappedField in unmapped:
                                    csvDF.drop(unmappedField, axis=1, inplace=True)
                                createLinkEntitiesDialog = ImportLinkEntitiesFromCSVFile(self, fieldsRemainingDF)

                                if createLinkEntitiesDialog.exec_():
                                    randomizePrimary = createLinkEntitiesDialog.randomizeLabel.isChecked()
                                    extraLink = createLinkEntitiesDialog.extraLinkLabel.isChecked()
                                    entityOneType = importLinksCSVDialog.entityOneTypeChoiceDropdown.currentText()
                                    entityTwoType = importLinksCSVDialog.entityTwoTypeChoiceDropdown.currentText()

                                    attributeRows = [comboBox.currentText() or fieldsRemainingDF.columns[index]
                                                     for index, comboBox
                                                     in enumerate(createLinkEntitiesDialog.fieldMappingComboBoxes)]

                                    entityTypeToImportAs = \
                                        createLinkEntitiesDialog.entityTypeChoiceDropdown.currentText()

                                    newEntityPrimaryAttribute = \
                                        self.parent().RESOURCEHANDLER.getPrimaryFieldForEntityType(entityTypeToImportAs)

                                    for entityRow, linkRow in zip(fieldsRemainingDF.itertuples(index=False),
                                                                  csvDF.itertuples(index=False)):

                                        linkJSON = {}
                                        entityOneJSON = {}
                                        entityTwoJSON = {}
                                        resolutionID = ""
                                        notes = ""

                                        for count, column in enumerate(linkRow):
                                            column = str(column)
                                            mapping = csvDF.columns[count]
                                            if mapping == 'Entity One':
                                                entityOneJSON = self.parent().LENTDB.getEntityOfType(column,
                                                                                                     entityOneType)
                                                # Add the entity if it doesn't exist.
                                                if entityOneJSON is None:
                                                    entityOneJSON = self.parent().LENTDB.addEntity({
                                                        self.parent().RESOURCEHANDLER.getPrimaryFieldForEntityType(
                                                            entityOneType): column, 'Entity Type': entityOneType})
                                            elif mapping == 'Entity Two':
                                                entityTwoJSON = self.parent().LENTDB.getEntityOfType(column,
                                                                                                     entityTwoType)
                                                # Add the entity if it doesn't exist.
                                                if entityTwoJSON is None:
                                                    entityTwoJSON = self.parent().LENTDB.addEntity({
                                                        self.parent().RESOURCEHANDLER.getPrimaryFieldForEntityType(
                                                            entityTwoType): column, 'Entity Type': entityTwoType})
                                            elif mapping == 'Notes':
                                                notes = column
                                            elif mapping == 'Resolution ID':
                                                resolutionID = column
                                            else:
                                                linkJSON[mapping] = column

                                        # We still need to check if both nodes exist, since errors may have occurred
                                        #   during their creation.
                                        if (entityOneJSON is not None) and (entityTwoJSON is not None):
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

                                            newEntityJSON = {str(value): str(entityRow[index]).strip()
                                                             for index, value in enumerate(attributeRows)}
                                            newEntityJSON['Entity Type'] = entityTypeToImportAs

                                            if randomizePrimary:
                                                newEntityJSON[newEntityPrimaryAttribute] += f' | {str(uuid4())}'

                                            newNode = self.parent().LENTDB.getEntityOfType(
                                                newEntityJSON[newEntityPrimaryAttribute], entityTypeToImportAs)
                                            if newNode is None:
                                                newNode = self.parent().LENTDB.addEntity(newEntityJSON,
                                                                                         updateTimeline=False)
                                            else:
                                                newNode.update(newEntityJSON)
                                                self.parent().LENTDB.addEntity(newNode, updateTimeline=False)

                                            linkJSONOne['uid'] = (entityOneJSON['uid'], newNode['uid'])
                                            linkJSONTwo['uid'] = (newNode['uid'], entityTwoJSON['uid'])

                                            if self.parent().LENTDB.addLink(linkJSONOne) is not None:
                                                newLinks.append((entityOneJSON['uid'], newNode['uid'],
                                                                 linkJSONOne['Resolution']))
                                            if self.parent().LENTDB.addLink(linkJSONTwo) is not None:
                                                newLinks.append((newNode['uid'], entityTwoJSON['uid'],
                                                                 linkJSONTwo['Resolution']))

                                            if extraLink:
                                                linkJSONThree = dict(linkJSON)
                                                linkJSONThree['uid'] = (entityOneJSON['uid'], entityTwoJSON['uid'])
                                                if self.parent().LENTDB.addLink(linkJSONThree) is not None:
                                                    newLinks.append((entityOneJSON['uid'], entityTwoJSON['uid'],
                                                                     linkJSONThree['Resolution']))

                                else:
                                    entityOneType = importLinksCSVDialog.entityOneTypeChoiceDropdown.currentText()
                                    entityTwoType = importLinksCSVDialog.entityTwoTypeChoiceDropdown.currentText()

                                    for row in csvDF.itertuples(index=False):
                                        linkJSON = {}
                                        entityOneJSON = {}
                                        entityTwoJSON = {}
                                        resolutionID = ""
                                        notes = ""

                                        for count, column in enumerate(row):
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

                                            if self.parent().LENTDB.addLink(linkJSON) is not None:
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
            justViewport = canvasSaveDialog.justViewportChoice.isChecked()
            transparentBackground = canvasSaveDialog.transparentChoice.isChecked()
            picture = self.parent().getPictureOfCanvas(canvas, justViewport, transparentBackground)
            picture.save(fileDirectory, "PNG")

    def save(self) -> None:
        self.parent().saveProject()

    def saveAs(self) -> None:
        self.parent().saveAsProject()

    def rename(self) -> None:
        self.parent().renameProjectPromptName()

    def openProjectFilesDir(self) -> None:
        self.parent().openDirectoryInNativeFileBrowser(self.parent().SETTINGS.value("Project/FilesDir"))

    def checkForUpdates(self) -> None:
        self.parent().openUpdateWindow()

    def editSettings(self) -> None:
        self.parent().editSettings()

    def editLogSettings(self) -> None:
        self.parent().editLogSettings()

    def editProjectSettings(self) -> None:
        self.parent().editProjectSettings()

    def editProgramSettings(self) -> None:
        self.parent().editProgramSettings()

    def editGraphicsSettings(self) -> None:
        self.parent().changeGraphics()

    def editResolutionsSettings(self) -> None:
        self.parent().editResolutionsSettings()

    def exitSoftware(self) -> None:
        self.parent().close()

    def reloadModules(self) -> None:
        self.parent().reloadModules()

    def viewModuleSources(self) -> None:
        self.parent().MODULEMANAGER.showSourcesManager()

    def viewModuleManager(self) -> None:
        self.parent().MODULEMANAGER.showModuleManager()

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

            if serverProjectDialog.exec():
                if serverProjectDialog.openProject:
                    self.parent().FCOM.openProject(serverProjectDialog.projectName,
                                                   serverProjectDialog.projectPass)
                else:
                    self.parent().FCOM.createProject(serverProjectDialog.projectName,
                                                     serverProjectDialog.projectPass)
        else:
            self.parent().MESSAGEHANDLER.warning('Not Connected to Server!', popUp=True)
            self.parent().setStatus('Must connect to a server before opening a project.')

    def serverCloseProject(self) -> None:
        self.parent().closeCurrentServerProject()

    def serverDeleteProject(self) -> None:
        if self.parent().FCOM.isConnected():
            current_project = self.parent().SETTINGS.value("Project/Server/Project")
            if current_project != "":
                confirmProjectDeleteDialog = DeleteProjectConfirmationDialog(self.parent(), current_project)
                if confirmProjectDeleteDialog.exec_():
                    self.parent().MESSAGEHANDLER.info('Deleting server project: ' + current_project)
                    self.parent().FCOM.deleteProject(current_project)
            else:
                self.parent().MESSAGEHANDLER.warning('Cannot Delete Server Project: No Server Project is '
                                                     'currently open!', popUp=True)
                self.parent().setStatus('Not connected to a Server Project, nothing to delete.')
        else:
            self.parent().MESSAGEHANDLER.warning('Cannot Delete Server Project: Not Connected to Server!', popUp=True)
            self.parent().setStatus('Not connected to Server, nothing to delete.')

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
        self.parent().syncDatabase()

    def uploadFiles(self) -> None:
        self.parent().uploadFiles()

    def downloadFiles(self) -> None:
        self.parent().downloadFiles()

    def manageCollectors(self) -> None:
        with self.parent().serverCollectorsLock:
            currentCollectors = dict(self.parent().collectors)
            runningCollectors = dict(self.parent().runningCollectors)
        collectorsDialog = CollectorsDialog(self.parent(),
                                            currentCollectors if self.parent().FCOM.isConnected() else None,
                                            runningCollectors)
        collectorsDialog.exec()

    def selectAllNodes(self) -> None:
        self.parent().centralWidget().tabbedPane.getCurrentScene().selectAllNodes()

    def selectChildNodes(self) -> None:
        self.parent().centralWidget().tabbedPane.getCurrentScene().selectChildNodes()

    def selectExpandChildNodes(self) -> None:
        self.parent().centralWidget().tabbedPane.getCurrentScene().selectChildNodes(clearSelection=False)

    def selectParentNodes(self) -> None:
        self.parent().centralWidget().tabbedPane.getCurrentScene().selectParentNodes()

    def selectExpandParentNodes(self) -> None:
        self.parent().centralWidget().tabbedPane.getCurrentScene().selectParentNodes(clearSelection=False)

    def viewMacrosWizard(self) -> None:
        self.parent().showMacrosDialog()

    def findEntityOrLink(self) -> None:
        self.parent().findEntityOrLinkOnCanvas()

    def findEntityOrLinkRegex(self) -> None:
        self.parent().findEntityOrLinkOnCanvas(regex=True)

    def findEntitiesOfType(self) -> None:
        self.parent().findEntityOfTypeOnCanvas()

    def findEntitiesOfTypeRegex(self) -> None:
        self.parent().findEntityOfTypeOnCanvas(regex=True)

    def findResolutions(self) -> None:
        self.parent().findResolution()

    def openWebsite(self) -> None:
        currentScene = self.parent().centralWidget().tabbedPane.getCurrentScene()
        for item in currentScene.selectedItems():
            if isinstance(item, BaseNode):
                itemJSON = self.parent().LENTDB.getEntity(item.uid)
                if itemJSON.get('Entity Type') == 'Website':
                    try:
                        QtGui.QDesktopServices.openUrl(itemJSON['URL'])
                    except KeyError:
                        continue

    def openURLs(self) -> None:
        currentScene = self.parent().centralWidget().tabbedPane.getCurrentScene()
        for item in currentScene.selectedItems():
            if isinstance(item, BaseNode):
                itemJSON = self.parent().LENTDB.getEntity(item.uid)
                for attribute in itemJSON:
                    if 'url' in attribute.lower():
                        value = itemJSON[attribute]
                        if isinstance(value, str):
                            try:
                                parsedValue = parse.urlparse(value)
                                if all([parsedValue.scheme, parsedValue.netloc]):
                                    QtGui.QDesktopServices.openUrl(value)
                            except (KeyError, AttributeError):
                                continue

    def searchOnline(self) -> None:
        currentScene = self.parent().centralWidget().tabbedPane.getCurrentScene()
        selectedURLs = SearchEngineDialog(self)

        if selectedURLs.exec_():
            selectedEngineURLs = [engineCheckbox.searchAttr for engineCheckbox in selectedURLs.searchEngineWidgets
                                  if engineCheckbox.isChecked()]
            searchTerms = []
            for item in currentScene.selectedItems():
                if isinstance(item, BaseNode):
                    itemJSON = self.parent().LENTDB.getEntity(item.uid)
                    primaryField = str(itemJSON[list(itemJSON)[1]])
                    primaryField = parse.quote(primaryField, "")
                    searchTerms.append('"' + primaryField + '"')
            for searchEngineURL in selectedEngineURLs:
                try:
                    QtGui.QDesktopServices.openUrl(searchEngineURL + " ".join(searchTerms))
                except KeyError:
                    continue

    def searchImageOnline(self) -> None:
        selectedURLs = SearchImageEngineDialog(self)

        if selectedURLs.exec_():
            selectedEngineURLs = [engineCheckbox.searchAttr for engineCheckbox in selectedURLs.searchEngineWidgets
                                  if engineCheckbox.isChecked()]
            for searchEngineURL in selectedEngineURLs:
                try:
                    QtGui.QDesktopServices.openUrl(searchEngineURL)
                except KeyError:
                    continue

    def rearrangeGraph(self) -> None:
        self.parent().centralWidget().tabbedPane.getCurrentScene().rearrangeGraph()

    def rearrangeGraphToTimeLine(self) -> None:
        self.parent().centralWidget().tabbedPane.getCurrentScene().rearrangeGraphTimeline()

    def generateReport(self):
        self.parent().generateReport()

    def queryWizard(self):
        self.parent().launchQueryWizard()

    def downloadWebsites(self) -> None:
        websiteEntities = []

        currentScene = self.parent().centralWidget().tabbedPane.getCurrentScene()
        for item in currentScene.selectedItems():
            if isinstance(item, BaseNode):
                itemJSON = self.parent().LENTDB.getEntity(item.uid)
                if itemJSON.get('Entity Type') == 'Website':
                    try:
                        websiteEntities.append((itemJSON['uid'], itemJSON['URL']))
                    except KeyError:
                        continue

        if not websiteEntities:
            self.parent().MESSAGEHANDLER.warning('Please select the "Website" nodes that correspond to the sites that '
                                                 'you wish to download, and re-run the Download Selected Websites '
                                                 'operation.',
                                                 popUp=True)
            return

        downloadThread = SaveWebsiteThread(self, self.parent(), websiteEntities)

        steps = len(websiteEntities) + 1
        progress = QtWidgets.QProgressDialog('Downloading websites, please wait...',
                                             'Abort', 0, steps, self.parent())
        progress.setMinimumDuration(1500)
        downloadThread.progressSignal.connect(progress.setValue)
        progress.canceled.connect(lambda: downloadThread.cancelOperation())
        downloadThread.start()

    def screenshotWebsites(self) -> None:
        websiteEntities = []
        currentScene = self.parent().centralWidget().tabbedPane.getCurrentScene()
        for item in currentScene.selectedItems():
            if isinstance(item, BaseNode):
                itemJSON = self.parent().LENTDB.getEntity(item.uid)
                if itemJSON.get('Entity Type') == 'Website':
                    try:
                        websiteEntities.append((itemJSON['uid'], itemJSON['URL']))
                    except KeyError:
                        continue

        if not websiteEntities:
            self.parent().MESSAGEHANDLER.warning('Please select the "Website" nodes that correspond to the sites that '
                                                 'you wish to download, and re-run the Download Selected Websites '
                                                 'operation.',
                                                 popUp=True)
            return

        screenshotThread = ScreenshotWebsiteThread(self, self.parent(), websiteEntities)

        steps = len(websiteEntities) + 1
        progress = QtWidgets.QProgressDialog('Screenshotting websites, please wait...',
                                             'Abort', 0, steps, self.parent())
        progress.setMinimumDuration(1500)
        screenshotThread.progressSignal.connect(progress.setValue)
        progress.canceled.connect(lambda: screenshotThread.cancelOperation())
        screenshotThread.start()

    def entityNotesToTextFile(self) -> None:
        baseFilesPath = Path(self.parent().SETTINGS.value('Project/FilesDir'))
        currentScene = self.parent().centralWidget().tabbedPane.getCurrentScene()

        newNodes = []
        for item in currentScene.selectedItems():
            if isinstance(item, BaseNode):
                itemJSON = self.parent().LENTDB.getEntity(item.uid)
                itemJSONNotes = itemJSON.get('Notes', '').strip()
                if itemJSONNotes != '':
                    itemPrimaryField = itemJSON[self.parent().RESOURCEHANDLER.getPrimaryFieldForEntityType(
                        itemJSON['Entity Type'])]
                    fileName = itemPrimaryField + '_' + itemJSON.get('Date Last Edited', str(time.time_ns())) + '.txt'
                    fileName = fileName.replace('/', '+')
                    fileName = fileName.replace('\\', '+')
                    with open(baseFilesPath / fileName, "w") as f:
                        f.write(itemJSONNotes)
                    newNodes.append([{'Document Name': fileName,
                                      'File Path': fileName,
                                      'Entity Type': 'Document'},
                                     {itemJSON['uid']: {'Resolution': 'Notes to Text File', 'Notes': ''}}])
        self.parent().facilitateResolutionSignalListener.emit('Notes to Text File Operation', newNodes)

    def extractCycles(self) -> None:
        self.parent().extractCycles()

    def importFromBrowser(self) -> None:
        """
        Import session tabs to canvas. Optionally, also take a screenshot of them.
        Assumes default browser profiles.

        :return:
        """
        if platform.system() not in ['Linux', 'Windows']:
            self.parent().setStatus('Importing tabs not supported on platforms other than Linux and Windows.')
            self.parent().MESSAGEHANDLER.warning('Importing tabs not supported on platforms '
                                                 'other than Linux and Windows.', popUp=True)
            return

        importDialog = BrowserImportDialog(self)

        if importDialog.exec_():
            importTabsThread = ImportBrowserTabsThread(importDialog, self.parent(), self)

            steps = 3
            progress = QtWidgets.QProgressDialog('Importing tabs, please wait...',
                                                 'Abort Import', 0, steps, self)
            progress.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            importTabsThread.progressSignal.connect(progress.setValue)
            progress.canceled.connect(lambda: importTabsThread.cancelOperation())
            importTabsThread.start()

    def importFromTORBrowser(self) -> None:
        """
        Import TOR session tabs to canvas.

        :return:
        """

        importDialog = TORBrowserImportDialog(self)

        if importDialog.exec_():
            importTorTabsThread = ImportTorBrowserTabsThread(importDialog, self.parent(), self)

            steps = 4
            progress = QtWidgets.QProgressDialog('Importing tabs, please wait...',
                                                 'Abort Import', 0, steps, self)
            progress.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            importTorTabsThread.progressSignal.connect(progress.setValue)
            progress.canceled.connect(lambda: importTorTabsThread.cancelOperation())
            importTorTabsThread.start()

    def firefoxCookiesHelper(self, cookiesDatabasePath: Path) -> list:
        """
        Used by threads to get firefox's cookies.
        @param cookiesDatabasePath:
        @return:
        """
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
            self.parent().warningSignalListener.emit('Could not access Firefox cookies.', True)
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

        return browserCookies

    def cookieFileHashHelper(self, filePath: Path):
        cookieHash = hashlib.md5()  # nosec
        with open(filePath, 'rb') as cookieFile:
            for chunk in iter(lambda: cookieFile.read(4096), b""):
                cookieHash.update(chunk)
        return cookieHash.digest()

    def importBrowserTabsFindings(self, resolution_result: list, canvasToImportTo: Union[str, None] = None) -> None:
        for finding in resolution_result:
            if len(finding) < 2:
                # Add dummy parents
                finding.append({'@^@^@^@': {'Resolution': 'Browser Import', 'Notes': ''}})
        newNodeUIDs = self.parent().centralWidget().tabbedPane.facilitateResolution('Importing Entities from Browser',
                                                                                    resolution_result)
        if canvasToImportTo:
            sceneToAddTo = self.parent().centralWidget().tabbedPane.getSceneByName(canvasToImportTo)
            for newNodeUID in newNodeUIDs:
                if newNodeUID is not None and newNodeUID not in sceneToAddTo.sceneGraph.nodes:
                    sceneToAddTo.addNodeProgrammatic(newNodeUID)
            sceneToAddTo.rearrangeGraph()


class DeleteProjectConfirmationDialog(QtWidgets.QDialog):

    def __init__(self, mainWindowObject, currentServerProject: str):
        super(DeleteProjectConfirmationDialog, self).__init__()
        self.setModal(True)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.mainWindowObject = mainWindowObject
        self.setWindowTitle('Delete Server Project')

        resolutionsLabel = QtWidgets.QLabel(f'Delete Project: "{currentServerProject}" ?')
        resolutionsLabel.setWordWrap(True)

        resolutionsLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(resolutionsLabel)

        buttonsWidget = QtWidgets.QWidget()
        buttonsWidgetLayout = QtWidgets.QHBoxLayout()
        buttonsWidget.setLayout(buttonsWidgetLayout)
        confirmButton = QtWidgets.QPushButton('Confirm')
        cancelButton = QtWidgets.QPushButton('Cancel')
        buttonsWidgetLayout.addWidget(cancelButton)
        buttonsWidgetLayout.addWidget(confirmButton)
        cancelButton.clicked.connect(self.reject)
        confirmButton.clicked.connect(self.accept)

        self.layout().addWidget(buttonsWidget)


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
        self.firefoxSessionChoice = QtWidgets.QCheckBox('Get entire session instead of latest tabs')
        firefoxGroupLayout.addWidget(self.firefoxChoice)
        firefoxGroupLayout.addWidget(self.firefoxSessionChoice)

        chromeGroup = QtWidgets.QGroupBox('Chrome Options')
        chromeGroupLayout = QtWidgets.QVBoxLayout()
        chromeGroup.setLayout(chromeGroupLayout)
        self.chromeChoice = QtWidgets.QCheckBox('Get tabs from Chrome / Chromium (Experimental)')
        chromeGroupLayout.addWidget(self.chromeChoice)

        dialogLayout.addWidget(firefoxGroup, 1, 0, 1, 2)
        dialogLayout.addWidget(chromeGroup, 2, 0, 1, 2)

        self.importScreenshotsCheckbox = QtWidgets.QCheckBox('Take screenshots of sites')
        dialogLayout.addWidget(self.importScreenshotsCheckbox, 3, 0, 1, 2)

        self.importToCanvasCheckbox = QtWidgets.QCheckBox('Import To Canvas:')
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


class TORBrowserImportDialog(QtWidgets.QDialog):

    def __init__(self, parent):
        super(TORBrowserImportDialog, self).__init__(parent=parent)
        self.setWindowTitle('Import TOR Browser Tabs')
        self.setModal(True)

        dialogLayout = QtWidgets.QGridLayout()
        self.setLayout(dialogLayout)
        self.entireSessionChoice = QtWidgets.QCheckBox('Get entire session instead of latest tabs')
        dialogLayout.addWidget(self.entireSessionChoice, 0, 0, 1, 2)
        self.importToCanvasCheckbox = QtWidgets.QCheckBox('Import To Canvas:')
        self.importToCanvasDropdown = QtWidgets.QComboBox()
        self.importToCanvasDropdown.addItems(list(parent.parent().centralWidget().tabbedPane.canvasTabs))
        self.importToCanvasDropdown.setEditable(False)
        self.importToCanvasDropdown.setDisabled(True)
        self.importToCanvasCheckbox.toggled.connect(lambda: self.importToCanvasDropdown.setDisabled(
            self.importToCanvasDropdown.isEnabled()))
        dialogLayout.addWidget(self.importToCanvasCheckbox, 1, 0, 1, 2)
        dialogLayout.addWidget(self.importToCanvasDropdown, 2, 0, 1, 2)

        acceptButton = QtWidgets.QPushButton('Accept')
        acceptButton.setAutoDefault(True)
        acceptButton.setDefault(True)
        cancelButton = QtWidgets.QPushButton('Cancel')
        acceptButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)
        acceptButton.setFocus()

        dialogLayout.addWidget(cancelButton, 4, 0, 1, 1)
        dialogLayout.addWidget(acceptButton, 4, 1, 1, 1)


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
        self.serverPasswordTextbox.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
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
        self.openProjectPassword.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
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
        self.createProjectPasswordTextbox.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
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

        resolutionsLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
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
            elif (not resolution[0].done) and resolution[0].return_results:
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


class CollectorsDialog(QtWidgets.QDialog):

    def __init__(self, mainWindow, collectorsDict: dict = None, runningCollectors: dict = None):
        super(CollectorsDialog, self).__init__()
        self.mainWindow = mainWindow
        self.baseLayout = QtWidgets.QVBoxLayout()
        self.setLayout(self.baseLayout)
        self.setModal(True)
        self.runningCollectorTreeItems = {}

        collectorsLabel = QtWidgets.QLabel("Collectors")
        collectorsLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.baseLayout.addWidget(collectorsLabel)

        if collectorsDict is None:
            notConnectedToServerLabel = QtWidgets.QLabel("Not connected to server, Collectors unavailable.")
            self.baseLayout.addWidget(notConnectedToServerLabel)
        else:
            connectedToServerFormWidget = QtWidgets.QWidget()
            self.connectedToServerFormWidgetLayout = QtWidgets.QVBoxLayout()

            for category in collectorsDict:
                categoryLabel = QtWidgets.QLabel(f"Category: {str(category)}")
                self.connectedToServerFormWidgetLayout.addWidget(categoryLabel)
                for collector in collectorsDict[category]:
                    newCollectorWidget = QtWidgets.QWidget()
                    newCollectorWidgetLayout = QtWidgets.QGridLayout()
                    newCollectorWidget.setLayout(newCollectorWidgetLayout)

                    newCollectorLabel = QtWidgets.QLabel(collectorsDict[category][collector]['name'])
                    newCollectorLabel.setToolTip(collectorsDict[category][collector]['description'])
                    newCollectorButton = QtWidgets.QPushButton('Create New')
                    newCollectorButton.clicked.connect(lambda: self.startSelectedCollector(
                        collectorsDict[category][collector]))

                    newCollectorWidgetLayout.addWidget(newCollectorLabel, 0, 0)
                    newCollectorWidgetLayout.addWidget(newCollectorButton, 0, 1)

                    newCollectorInstanceTree = QtWidgets.QTreeWidget()
                    newCollectorInstanceTree.setColumnCount(2)
                    newCollectorInstanceTree.setHeaderLabels(['UID', 'Stop Button'])
                    newCollectorInstanceTree.setSelectionBehavior(
                        QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
                    newCollectorInstanceTree.header().setStretchLastSection(False)
                    newCollectorInstanceTree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
                    newCollectorWidgetLayout.addWidget(newCollectorInstanceTree, 1, 0, 2, 2)

                    if runningCollectors is not None:
                        for value in runningCollectors.values():
                            for runningCollector in value[collector]:
                                newTreeItem = QtWidgets.QTreeWidgetItem(newCollectorInstanceTree)
                                newTreeItem.setText(0, runningCollector['uid'])
                                stopButton = QtWidgets.QPushButton("Stop")
                                stopButton.clicked.connect(lambda: self.stopSelectedCollector(runningCollector['uid']))
                                newCollectorInstanceTree.setItemWidget(newTreeItem, 1, stopButton)
                                self.runningCollectorTreeItems[runningCollector['uid']] = (newTreeItem,
                                                                                           newCollectorInstanceTree)

                    self.connectedToServerFormWidgetLayout.addWidget(newCollectorWidget)

            connectedToServerFormWidget.setLayout(self.connectedToServerFormWidgetLayout)

            self.baseLayout.addWidget(connectedToServerFormWidget)

        closeButton = QtWidgets.QPushButton('Close')
        closeButton.clicked.connect(self.accept)

        self.baseLayout.addWidget(closeButton)

    def startSelectedCollector(self, collectorToStartDict: dict):
        newCollector = CollectorStartDialog(self.mainWindow, collectorToStartDict)

        if newCollector.exec_():
            collector_name = collectorToStartDict['name']
            try:
                self.mainWindow.FCOM.startServerCollector(collector_name,
                                                          newCollector.chosenItems,
                                                          newCollector.chosenParameters)
                self.mainWindow.MESSAGEHANDLER.info('Starting server collector: ' + collector_name)
            except Exception as e:
                self.mainWindow.MESSAGEHANDLER.error(f'Error starting server collector: {str(e)}')

    def stopSelectedCollector(self, collectorToStop: str):
        self.mainWindow.MESSAGEHANDLER.info(f'Stopping server collector with UID: {collectorToStop}')
        self.mainWindow.FCOM.stopServerCollector(collectorToStop)
        self.runningCollectorTreeItems[collectorToStop][1].takeTopLevelItem(
            self.runningCollectorTreeItems[collectorToStop][1].indexOfTopLevelItem(
                self.runningCollectorTreeItems[collectorToStop][0]))
        currentClientCollectors = self.mainWindow.getClientCollectors()
        try:
            currentClientCollectors.pop(collectorToStop)
            self.mainWindow.stopRunningCollector(collectorToStop)
            self.mainWindow.setClientCollectors(currentClientCollectors)
        except KeyError:
            self.mainWindow.MESSAGEHANDLER.error('Trying to stop Collector that was never ran. Was confirmation that '
                                                 'the collector was started by the server received?', popUp=False)


class CollectorStartDialog(QtWidgets.QDialog):

    def __init__(self, mainWindow, collectorDict: dict):
        super(CollectorStartDialog, self).__init__()
        self.mainWindow = mainWindow
        self.setModal(True)
        self.setWindowTitle('Collector Wizard')
        self.parametersList = []
        self.chosenParameters = {}
        self.chosenItems = []

        dialogLayout = QtWidgets.QGridLayout()
        self.setLayout(dialogLayout)
        self.childWidget = QtWidgets.QTabWidget()
        dialogLayout.addWidget(self.childWidget, 0, 0, 4, 2)
        dialogLayout.setRowStretch(0, 1)
        dialogLayout.setColumnStretch(0, 1)

        entitySelectTab = QtWidgets.QWidget()
        entitySelectTab.setLayout(QtWidgets.QVBoxLayout())
        originTypes = collectorDict['originTypes']
        labelText = collectorDict['description'] + "\n\n"
        labelText += 'Select the entities to use for this collector.\nAccepted Origin Types: ' + \
                     ', '.join(collectorDict['originTypes'])
        entitySelectTabLabel = QtWidgets.QLabel(labelText)
        entitySelectTabLabel.setWordWrap(True)
        entitySelectTabLabel.setMaximumWidth(600)

        entitySelectTabLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        entitySelectTab.layout().addWidget(entitySelectTabLabel)

        self.entitySelector = QtWidgets.QTreeWidget()
        self.entitySelector.setHeaderLabels(['Primary Field', 'Entity Type', 'Icon'])
        self.entitySelector.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.entitySelector.setSortingEnabled(True)
        # Stretch the first column, since it contains the primary field.
        self.entitySelector.header().setStretchLastSection(False)
        self.entitySelector.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        relevantEntityFields = [(entity['uid'], entity[list(entity)[1]], entity['Entity Type'], entity['Icon'])
                                for entity in self.mainWindow.LENTDB.getAllEntities()
                                if entity['Entity Type'] in originTypes or '*' in originTypes]
        for eligibleEntity in relevantEntityFields:
            newTreeWidgetItem = QtWidgets.QTreeWidgetItem(self.entitySelector)
            newTreeWidgetItemPixmap = QtGui.QPixmap()
            resizedIcon = resizePictureFromBuffer(eligibleEntity[3], (40, 40))
            newTreeWidgetItemPixmap.loadFromData(resizedIcon)
            newTreeWidgetItem.setText(0, eligibleEntity[1])
            newTreeWidgetItem.setText(1, eligibleEntity[2])
            newTreeWidgetItem.setIcon(2, newTreeWidgetItemPixmap)
            # Hidden, so we can pull the UID later.
            newTreeWidgetItem.setText(3, eligibleEntity[0])

        self.entitySelector.setSelectionMode(self.entitySelector.SelectionMode.MultiSelection)
        entitySelectTab.layout().addWidget(self.entitySelector)

        self.childWidget.addTab(entitySelectTab, 'Entities')

        parameters = collectorDict['parameters']
        for key in parameters:
            propertyWidget = QtWidgets.QWidget()
            propertyKeyLayout = QtWidgets.QVBoxLayout()
            propertyWidget.setLayout(propertyKeyLayout)

            propertyLabel = QtWidgets.QLabel(parameters[key].get('description'))
            propertyLabel.setWordWrap(True)
            propertyLabel.setMaximumWidth(600)

            propertyLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            propertyKeyLayout.addWidget(propertyLabel)

            propertyType = parameters[key].get('type')
            propertyValue = parameters[key].get('value')
            propertyDefaultValue = parameters[key].get('default')

            if propertyType == 'String':
                propertyInputField = StringPropertyInput(propertyValue, propertyDefaultValue)
            elif propertyType == 'File':
                propertyInputField = FilePropertyInput(propertyValue, propertyDefaultValue)
            elif propertyType == 'SingleChoice':
                propertyInputField = SingleChoicePropertyInput(propertyValue, propertyDefaultValue)
            elif propertyType == 'MultiChoice':
                propertyInputField = MultiChoicePropertyInput(propertyValue, propertyDefaultValue)
            else:
                # If value has invalid type, skip to the next property.
                propertyInputField = None

            if propertyInputField is not None:
                propertyKeyLayout.addWidget(propertyInputField)

            propertyKeyLayout.setStretch(1, 1)

            self.childWidget.addTab(propertyWidget, key)
            self.parametersList.append((key, propertyInputField))

        nextButton = QtWidgets.QPushButton('Next')
        nextButton.clicked.connect(self.nextTab)
        previousButton = QtWidgets.QPushButton('Previous')
        previousButton.clicked.connect(self.previousTab)
        acceptButton = QtWidgets.QPushButton('Accept')
        acceptButton.setAutoDefault(True)
        acceptButton.setDefault(True)
        acceptButton.clicked.connect(self.accept)
        cancelButton = QtWidgets.QPushButton('Cancel')
        cancelButton.clicked.connect(self.reject)

        dialogLayout.addWidget(previousButton, 4, 0, 1, 1)
        dialogLayout.addWidget(nextButton, 4, 1, 1, 1)
        dialogLayout.addWidget(cancelButton, 5, 0, 1, 1)
        dialogLayout.addWidget(acceptButton, 5, 1, 1, 1)

    def nextTab(self):
        currentIndex = self.childWidget.currentIndex()
        if currentIndex < self.childWidget.count():
            self.childWidget.setCurrentIndex(currentIndex + 1)

    def previousTab(self):
        currentIndex = self.childWidget.currentIndex()
        if currentIndex > 0:
            self.childWidget.setCurrentIndex(currentIndex - 1)

    def accept(self) -> None:
        for item in self.entitySelector.selectedItems():
            self.chosenItems.append(self.mainWindow.LENTDB.getEntity(item.text(3)))
        for resolutionParameterName, resolutionParameterInput in self.parametersList:
            value = resolutionParameterInput.getValue()
            if value == '':
                msgBox = QtWidgets.QMessageBox()
                msgBox.setModal(True)
                QtWidgets.QMessageBox.warning(msgBox,
                                              "Not all parameters were filled in",
                                              "Some of the required parameters for the collector have been left blank."
                                              " Please fill them in before proceeding.")
                return
            self.chosenParameters[resolutionParameterName] = value

        super(CollectorStartDialog, self).accept()


class ImportLinksFromCSVFile(QtWidgets.QDialog):

    def __init__(self, parent, csvTableContents: pd.DataFrame):
        super(ImportLinksFromCSVFile, self).__init__(parent=parent)

        self.setModal(True)
        importLayout = QtWidgets.QVBoxLayout()
        self.setLayout(importLayout)
        self.setWindowTitle("Import Links from CSV")

        columnNumber = len(csvTableContents.columns)

        titleLabel = QtWidgets.QLabel("Import Links from CSV")
        titleLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

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
        for _ in range(columnNumber):
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
                columnItem.setFlags(columnItem.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                csvTable.setItem(rowValues[0], column, columnItem)

        randomizationLabel = QtWidgets.QLabel("If the resolution identifiers (i.e. 'Resolution ID') are not guaranteed "
                                              "to be unique, you can configure whether you'd like to leave them as-is, "
                                              "append a random token, or ignore any resolution identifiers and just "
                                              "have random tokens as the Resolution IDs.\nPlease select what you would "
                                              "like to do:")
        randomizationLabel.setWordWrap(True)
        randomizationLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
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
        for comboBox, checkBox in zip(self.fieldMappingComboBoxes, self.fieldIncludeCheckBoxes):
            if comboBox.currentIndex() == newIndex:
                if newIndex == 0:
                    checkBox.setEnabled(True)
                else:
                    if comboBox.hasFocus():
                        checkBox.setEnabled(False)
                        checkBox.setChecked(True)
                    else:
                        comboBox.setCurrentIndex(0)
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

        self.setModal(True)
        importLayout = QtWidgets.QVBoxLayout()
        self.setLayout(importLayout)
        self.setWindowTitle("Create Entities from Link Fields")

        columnNumber = len(csvTableContents.columns)

        titleLabel = QtWidgets.QLabel("Create Entities from Link Fields")
        titleLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

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

        self.randomizeLabel = QtWidgets.QCheckBox('Add random token to Primary Field?')
        self.randomizeLabel.setToolTip("Choose whether you want to append a random token to the primary fields of "
                                       "the imported entities.")
        self.randomizeLabel.setChecked(True)

        self.extraLinkLabel = QtWidgets.QCheckBox('Include links bypassing imported entities?')
        self.extraLinkLabel.setToolTip("Check this box if you want links created between the parent and child "
                                       "entities, as well as links between the parent, new node and child entities.")
        self.extraLinkLabel.setChecked(False)

        self.fieldMappingComboBoxes = []
        tableFieldAttributeMapping = QtWidgets.QWidget()
        tableFieldAttributeMappingLayout = QtWidgets.QHBoxLayout()
        tableFieldAttributeMapping.setLayout(tableFieldAttributeMappingLayout)
        for _ in range(columnNumber):
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
                columnItem.setFlags(columnItem.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
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
        importLayout.addWidget(self.randomizeLabel)
        importLayout.addWidget(self.extraLinkLabel)
        importLayout.addWidget(buttonsWidget)

        self.pickEntityToImportAs()

    def pickEntityToImportAs(self):
        currentEntityAttributes = [''] + self.parent().parent().RESOURCEHANDLER.getEntityAttributes(
            self.entityTypeChoiceDropdown.currentText())
        for comboBox in self.fieldMappingComboBoxes:
            comboBox.blockSignals(True)
            comboBox.clear()
            comboBox.blockSignals(False)
            comboBox.addItems(currentEntityAttributes)

    def changeMappingForField(self, newIndex):
        for comboBox in self.fieldMappingComboBoxes:
            if comboBox.currentIndex() == newIndex and not comboBox.hasFocus():
                comboBox.setCurrentIndex(0)

    def confirmThatPrimaryFieldIsMapped(self):
        primaryField = self.parent().parent().RESOURCEHANDLER.getPrimaryFieldForEntityType(
            self.entityTypeChoiceDropdown.currentText())
        primaryFieldMapped = any(comboBox.currentText() == primaryField for comboBox in self.fieldMappingComboBoxes)
        if primaryFieldMapped:
            self.accept()
        else:
            self.parent().parent().MESSAGEHANDLER.warning('Primary field (' + primaryField +
                                                          ') needs to be mapped before proceeding.', popUp=True)


class ImportEntityFromCSVFile(QtWidgets.QDialog):

    def __init__(self, parent, csvTableContents: pd.DataFrame):
        super(ImportEntityFromCSVFile, self).__init__(parent=parent)

        self.setModal(True)
        importLayout = QtWidgets.QVBoxLayout()
        self.setLayout(importLayout)
        self.setWindowTitle("Import Entities from CSV")

        columnNumber = len(csvTableContents.columns)

        titleLabel = QtWidgets.QLabel("Import Entities from CSV")
        titleLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

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
        for _ in range(columnNumber):
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
                columnItem.setFlags(columnItem.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                csvTable.setItem(rowValues[0], column, columnItem)

        importToCanvasChoiceWidget = QtWidgets.QWidget()
        importToCanvasChoiceLayout = QtWidgets.QHBoxLayout()
        importToCanvasChoiceWidget.setLayout(importToCanvasChoiceLayout)
        self.importToCanvasCheckbox = QtWidgets.QCheckBox('Import To Canvas:')
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
            comboBox.blockSignals(True)
            comboBox.clear()
            comboBox.blockSignals(False)
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
            self.parent().parent().MESSAGEHANDLER.warning(
                f'Primary field ({primaryField}) needs to be mapped before proceeding.', popUp=True)


class ImportFromFileDialog(QtWidgets.QDialog):

    def popupFileDialog(self):
        self.fileDirectory = QtWidgets.QFileDialog().getOpenFileName(
            parent=self, caption='Select File to Import From',
            dir=str(Path.home()),
            options=QtWidgets.QFileDialog.Option.DontUseNativeDialog,
            filter="Import File (*.csv *.txt *.xls *.xlsx *.ods)")[0]
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
        descriptionLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        descriptionLabel.setWordWrap(True)
        dialogLayout.addWidget(descriptionLabel, 0, 0, 1, 2)

        self.fileDirectoryButton = QtWidgets.QPushButton("Select file...")
        self.fileDirectoryLine = QtWidgets.QLineEdit()
        self.fileDirectoryLine.setReadOnly(True)

        fileChoiceLabel = QtWidgets.QLabel('Specify the type of the chosen file and what to import:')
        fileChoiceLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        fileChoiceLabel.setWordWrap(True)

        self.textFileChoice = QtWidgets.QRadioButton('Text file - Entities Import')
        self.textFileChoice.setChecked(True)
        self.CSVFileChoice = QtWidgets.QRadioButton('Spreadsheet / CSV - Entities Import')
        self.CSVFileChoiceLinks = QtWidgets.QRadioButton('Spreadsheet / CSV - Links Import')

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
        descriptionLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
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
        for lineIndex, lineValue in enumerate(fileContents):
            columnItem = QtWidgets.QTableWidgetItem(lineValue)
            columnItem.setFlags(columnItem.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            textTable.setItem(lineIndex, 0, columnItem)
        textTable.setColumnWidth(0, 450)
        textTable.setHorizontalHeaderLabels(['File Entities Preview'])

        dialogLayout.addWidget(textTable, 3, 0, 1, 2)

        self.importToCanvasCheckbox = QtWidgets.QCheckBox('Import To Canvas:')
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

        dialogLayout = QtWidgets.QGridLayout()
        self.setLayout(dialogLayout)
        descriptionLabel = QtWidgets.QLabel('Choose the directory to save the Picture to:')
        descriptionLabel.setWordWrap(True)
        dialogLayout.addWidget(descriptionLabel, 0, 0, 1, 2)

        self.fileDirectoryButton = QtWidgets.QPushButton("Select directory...")
        self.fileDirectoryLine = QtWidgets.QLineEdit()
        self.fileDirectoryLine.setReadOnly(True)

        self.backgroundButtonsGroup = QtWidgets.QButtonGroup()
        self.canvasViewportButtonsGroup = QtWidgets.QButtonGroup()

        self.transparentChoice = QtWidgets.QRadioButton('Transparent')
        self.backgroundButtonsGroup.addButton(self.transparentChoice)
        self.transparentChoice.setChecked(True)
        self.withBackgroundChoice = QtWidgets.QRadioButton('With Background')
        self.backgroundButtonsGroup.addButton(self.withBackgroundChoice)
        self.justViewportChoice = QtWidgets.QRadioButton('Just Viewport')
        self.justViewportChoice.setToolTip('Save a picture of only the contents of the scene that are currently '
                                           'visible (through the viewport).')
        self.justViewportChoice.setChecked(True)
        self.canvasViewportButtonsGroup.addButton(self.justViewportChoice)
        self.entireCanvasChoice = QtWidgets.QRadioButton('Entire Canvas')
        self.entireCanvasChoice.setToolTip('Save a picture of the entire contents of the canvas, not just the current '
                                           'viewport contents.')
        self.canvasViewportButtonsGroup.addButton(self.entireCanvasChoice)

        dialogLayout.addWidget(self.fileDirectoryLine, 1, 0, 1, 2)
        dialogLayout.addWidget(self.fileDirectoryButton, 2, 0, 1, 2)
        dialogLayout.addWidget(self.transparentChoice, 3, 0, 1, 1)
        dialogLayout.addWidget(self.withBackgroundChoice, 3, 1, 1, 1)
        dialogLayout.addWidget(self.justViewportChoice, 4, 0, 1, 1)
        dialogLayout.addWidget(self.entireCanvasChoice, 4, 1, 1, 1)

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
        saveAsDialog.setOption(QtWidgets.QFileDialog.Option.DontUseNativeDialog, True)
        saveAsDialog.setViewMode(QtWidgets.QFileDialog.ViewMode.List)
        saveAsDialog.setNameFilter("Image (*.png)")
        saveAsDialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        saveAsDialog.setDirectory(str(Path.home()))
        saveAsDialog.exec()
        self.fileDirectory = saveAsDialog.selectedFiles()[0]
        if self.fileDirectory != '':
            if Path(self.fileDirectory).suffix != 'png':
                self.fileDirectory = str(Path(self.fileDirectory).with_suffix('.png'))
            self.fileDirectoryLine.setText(self.fileDirectory)


class SearchEngineDialog(QtWidgets.QDialog):
    searchEngines = ['https://www.startpage.com/sp/search?q=', 'https://html.duckduckgo.com/html?q=',
                     'https://www.google.com/search?q=', 'https://www.bing.com/search?q=',
                     'https://www.yandex.com/search/?text=', 'https://gigablast.com/search?q=',
                     'https://www.etools.ch/searchSubmit.do?query=', 'https://lite.qwant.com/?q=',
                     'https://www.izito.com/search?q=', 'https://searx.org/search?q=']

    def __init__(self, parent):
        super(SearchEngineDialog, self).__init__(parent=parent)
        self.setWindowTitle('Search Engine Lookup')
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        dialogLabel = QtWidgets.QLabel('Select the search engines to use:')
        layout.addWidget(dialogLabel)

        self.searchEngineWidgets = []

        for engine in self.searchEngines:
            engineCheckbox = QtWidgets.QCheckBox('/'.join(engine.split('/')[:3]))
            engineCheckbox.searchAttr = engine
            layout.addWidget(engineCheckbox)
            self.searchEngineWidgets.append(engineCheckbox)

        buttonsWidget = QtWidgets.QWidget()
        buttonsWidgetLayout = QtWidgets.QHBoxLayout()
        buttonsWidget.setLayout(buttonsWidgetLayout)
        acceptButton = QtWidgets.QPushButton('Confirm')
        cancelButton = QtWidgets.QPushButton('Cancel')
        cancelButton.clicked.connect(self.reject)
        acceptButton.clicked.connect(self.accept)
        buttonsWidgetLayout.addWidget(cancelButton)
        buttonsWidgetLayout.addWidget(acceptButton)

        layout.addWidget(buttonsWidget)


class SearchImageEngineDialog(QtWidgets.QDialog):
    searchEngines = ['https://pimeyes.com/en', 'https://yandex.com/images/',
                     'https://www.bing.com/visualsearch ', 'https://www.google.com/imghp',
                     'https://tineye.com/']

    def __init__(self, parent):
        super(SearchImageEngineDialog, self).__init__(parent=parent)
        self.setWindowTitle('Image Search Engine Lookup')
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        dialogLabel = QtWidgets.QLabel('Select the image search engines to open in tabs:')
        layout.addWidget(dialogLabel)

        self.searchEngineWidgets = []

        for engine in self.searchEngines:
            engineCheckbox = QtWidgets.QCheckBox('/'.join(engine.split('/')[:3]))
            engineCheckbox.searchAttr = engine
            layout.addWidget(engineCheckbox)
            self.searchEngineWidgets.append(engineCheckbox)

        buttonsWidget = QtWidgets.QWidget()
        buttonsWidgetLayout = QtWidgets.QHBoxLayout()
        buttonsWidget.setLayout(buttonsWidgetLayout)
        acceptButton = QtWidgets.QPushButton('Confirm')
        cancelButton = QtWidgets.QPushButton('Cancel')
        cancelButton.clicked.connect(self.reject)
        acceptButton.clicked.connect(self.accept)
        buttonsWidgetLayout.addWidget(cancelButton)
        buttonsWidgetLayout.addWidget(acceptButton)

        layout.addWidget(buttonsWidget)


class ScreenshotWebsiteThread(QtCore.QThread):
    progressSignal = QtCore.Signal(int)
    cancelled = False

    def __init__(self, menuBar, mainWindow, websiteEntities):
        super(ScreenshotWebsiteThread, self).__init__()
        self.mainWindow = mainWindow
        self.menuBar = menuBar
        self.websiteEntities = websiteEntities

    def cancelOperation(self):
        self.cancelled = True

    def run(self) -> None:
        baseFilesPath = Path(self.mainWindow.SETTINGS.value('Project/FilesDir'))
        progressValue = 1
        self.progressSignal.emit(progressValue)

        newNodes = []

        with sync_playwright() as p:
            browser = p.firefox.launch(executable_path=self.mainWindow.getPlaywrightBrowserPath('firefox'))

            if platform.system() == 'Linux':
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent=user_agents['Firefox']['Linux'][0]
                )
                urlPath = Path.home() / '.mozilla' / 'firefox'
                if not (urlPath / 'profiles.ini').exists():
                    urlPath = Path.home() / 'snap' / 'firefox' / 'common' / '.mozilla' / 'firefox'
            else:  # We already checked before that the platform is either 'Linux' or 'Windows'.
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent=user_agents['Firefox']['Windows'][0]
                )
                urlPath = Path(os.environ['APPDATA']) / 'Mozilla' / 'Firefox' / 'Profiles'

            if tabsFilePath := list(urlPath.glob('*default*/sessionstore-backups/recovery.jsonlz4')):
                tabsFilePath = tabsFilePath[0]
                cookiesDatabasePath = tabsFilePath.parent.parent / 'cookies.sqlite'
                browserCookies = self.menuBar.firefoxCookiesHelper(cookiesDatabasePath)
                context.add_cookies(browserCookies)
            page = context.new_page()

            for websiteEntity in self.websiteEntities:
                if self.cancelled:
                    break
                website = websiteEntity[1]
                screenshotName = tldextract.extract(website).fqdn + ' Screenshot ' + str(time.time_ns()) + '.png'
                currFileName = baseFilesPath / screenshotName

                for _ in range(3):
                    try:
                        page.goto(website)
                        page.wait_for_load_state("networkidle")
                        page.screenshot(path=str(currFileName), full_page=True)
                        break
                    except TimeoutError:
                        pass
                progressValue += 1
                self.progressSignal.emit(progressValue)

                newNodes.append([{'Image Name': screenshotName,
                                  'File Path': screenshotName,
                                  'Entity Type': 'Image'},
                                 {websiteEntity[0]: {'Resolution': 'Website Screenshot', 'Notes': ''}}])

            context.close()
            browser.close()
        self.progressSignal.emit(len(self.websiteEntities) + 1)
        self.mainWindow.facilitateResolutionSignalListener.emit('Screenshot Websites Operation', newNodes)


class SaveWebsiteThread(QtCore.QThread):
    progressSignal = QtCore.Signal(int)
    cancelled = False

    def __init__(self, menuBar, mainWindow, websiteEntities):
        super(SaveWebsiteThread, self).__init__()
        self.mainWindow = mainWindow
        self.menuBar = menuBar
        self.websiteEntities = websiteEntities

    def cancelOperation(self):
        self.cancelled = True

    def run(self) -> None:
        newNodes = []
        baseFilesPath = Path(self.mainWindow.SETTINGS.value('Project/FilesDir'))
        currTempDir = Path.home()  # Failsafe in case we can't make directories in TEMP / tmp.

        progressValue = 1
        self.progressSignal.emit(progressValue)

        def handle_response(response):
            responseURL = response.url
            responseURLFragments = responseURL.split('/')[3:]
            savePath = currTempDir
            with contextlib.suppress(Exception):
                if response.ok:
                    for fragment in responseURLFragments[:-1]:
                        savePath /= fragment
                        savePath.mkdir(exist_ok=True)
                    try:
                        filename = responseURLFragments[-1]
                    except IndexError:
                        filename = ''
                    if not filename:
                        filename = 'index.html'
                    with open(savePath / filename, "wb") as fileToWrite:
                        fileToWrite.write(response.body())

        with sync_playwright() as p:
            browser = p.firefox.launch(executable_path=self.mainWindow.getPlaywrightBrowserPath('firefox'))

            if platform.system() == 'Linux':
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent=user_agents['Firefox']['Linux'][0]
                )
                urlPath = Path.home() / '.mozilla' / 'firefox'
                if not (urlPath / 'profiles.ini').exists():
                    urlPath = Path.home() / 'snap' / 'firefox' / 'common' / '.mozilla' / 'firefox'
            else:  # We already checked before that the platform is either 'Linux' or 'Windows'.
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent=user_agents['Firefox']['Windows'][0]
                )
                urlPath = Path(os.environ['APPDATA']) / 'Mozilla' / 'Firefox' / 'Profiles'

            if tabsFilePath := list(urlPath.glob('*default*/sessionstore-backups/recovery.jsonlz4')):
                tabsFilePath = tabsFilePath[0]
                cookiesDatabasePath = tabsFilePath.parent.parent / 'cookies.sqlite'
                browserCookies = self.menuBar.firefoxCookiesHelper(cookiesDatabasePath)
                context.add_cookies(browserCookies)
            page = context.new_page()
            page.on("response", handle_response)

            for websiteEntity in self.websiteEntities:
                if self.cancelled:
                    break
                website = websiteEntity[1]
                with tempfile.TemporaryDirectory() as tempDir:
                    currTempDir = Path(tempDir)
                    archiveDir = baseFilesPath / (tldextract.extract(website).fqdn + ' Snapshot ' + str(time.time_ns()))

                    for _ in range(3):
                        with contextlib.suppress(TimeoutError):
                            page.goto(website)
                            page.keyboard.press("End")
                            page.wait_for_load_state("networkidle")
                            break
                    progressValue += 1
                    self.progressSignal.emit(progressValue)

                    newNodeName = Path(shutil.make_archive(str(archiveDir), 'zip', currTempDir)).relative_to(
                        baseFilesPath)
                    newNodes.append([{'Archive Name': str(newNodeName),
                                      'File Path': str(newNodeName),
                                      'Entity Type': 'Archive'},
                                     {websiteEntity[0]: {'Resolution': 'Website Snapshot', 'Notes': ''}}])
            context.close()
            browser.close()
        self.progressSignal.emit(len(self.websiteEntities) + 1)
        self.mainWindow.facilitateResolutionSignalListener.emit('Download Websites Operation', newNodes)


class ImportBrowserTabsThread(QtCore.QThread):
    progressSignal = QtCore.Signal(int)
    cancelled = False

    def __init__(self, importDialog: BrowserImportDialog, mainWindowObject, menuObject):
        super(ImportBrowserTabsThread, self).__init__(parent=mainWindowObject)
        self.importDialog = importDialog
        self.mainWindow = mainWindowObject
        self.menuObject = menuObject

    def cancelOperation(self):
        self.cancelled = True

    def run(self) -> None:

        progressValue = 1
        self.progressSignal.emit(progressValue)

        returnResults = []

        with sync_playwright() as p:
            if self.importDialog.firefoxChoice.isChecked():
                recordSession = self.importDialog.firefoxSessionChoice.isChecked()
                try:
                    browser = p.firefox.launch(executable_path=self.mainWindow.getPlaywrightBrowserPath('firefox'))

                    if platform.system() == 'Linux':
                        context = browser.new_context(
                            viewport={'width': 1920, 'height': 1080},
                            user_agent=user_agents['Firefox']['Linux'][0]
                        )
                        urlPath = Path.home() / '.mozilla' / 'firefox'
                        if not (urlPath / 'profiles.ini').exists():
                            urlPath = Path.home() / 'snap' / 'firefox' / 'common' / '.mozilla' / 'firefox'
                    else:  # We already checked before that the platform is either 'Linux' or 'Windows'.
                        context = browser.new_context(
                            viewport={'width': 1920, 'height': 1080},
                            user_agent=user_agents['Firefox']['Windows'][0]
                        )
                        urlPath = Path(os.environ['APPDATA']) / 'Mozilla' / 'Firefox' / 'Profiles'

                    if tabsFilePath := list(urlPath.glob('*default*/sessionstore-backups/recovery.jsonlz4')):
                        tabsFilePath = tabsFilePath[0]
                        if recordSession:
                            tabsToOpen = []
                        else:
                            tabsToOpen = set()
                        sitesScreenshotted = set()

                        tabsBytes = tabsFilePath.read_bytes()
                        if tabsBytes[:8] == b'mozLz40\0':
                            tabsBytes = lz4.block.decompress(tabsBytes[8:])
                        tabsJson = json.loads(tabsBytes)
                        for browserWindow in tabsJson['windows']:
                            for browserTab in browserWindow['tabs']:
                                if recordSession:
                                    first = True
                                    for browserEntry in browserTab['entries']:
                                        url = browserEntry['url']
                                        title = browserEntry.get('title', '')
                                        if not url.startswith('about:'):
                                            if first:
                                                tabsToOpen.append((url, title, True))
                                                first = False
                                            else:
                                                tabsToOpen.append((url, title, False))
                                else:
                                    browserEntry = browserTab['entries'][browserTab['index'] - 1]
                                    url = browserEntry['url']
                                    if not url.startswith('about:'):
                                        tabsToOpen.add((url, browserEntry['title']))

                        cookiesDatabasePath = tabsFilePath.parent.parent / 'cookies.sqlite'
                        browserCookies = self.menuObject.firefoxCookiesHelper(cookiesDatabasePath)
                        context.add_cookies(browserCookies)
                        page = context.new_page()

                        projectFilesDir = Path(self.mainWindow.SETTINGS.value("Project/FilesDir"))

                        historyMark = -1
                        for tabToOpen in tabsToOpen:
                            if self.cancelled:
                                break
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
                                    newEntity = [{'Document Name': urlTitle,
                                                  'File Path': urlPath,
                                                  'Entity Type': 'Document'}]
                                elif 'image' in pathType:
                                    newEntity = [{'Image Name': urlTitle,
                                                  'File Path': urlPath,
                                                  'Entity Type': 'Image'}]
                                elif 'video' in pathType:
                                    newEntity = [{'Video Name': urlTitle,
                                                  'File Path': urlPath,
                                                  'Entity Type': 'Video'}]
                                elif 'archive' in pathType:
                                    newEntity = [{'Archive Name': urlTitle,
                                                  'File Path': urlPath,
                                                  'Entity Type': 'Archive'}]

                            elif parsedURL.scheme.startswith('http'):
                                newEntity = [{'URL': actualURL,
                                              'Entity Type': 'Website'}]

                                if self.importDialog.importScreenshotsCheckbox.isChecked():
                                    # If we time out, take a screenshot of the page as-is.
                                    try:
                                        page.goto(actualURL)
                                    except TimeoutError:
                                        pass

                                    # Don't screenshot sites multiple times.
                                    # Save in new variable to guard against redirects.
                                    pageURL = page.url
                                    if pageURL not in sitesScreenshotted:
                                        sitesScreenshotted.add(pageURL)

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
                                            screenshotSavePath = screenshotSavePath.replace('\\', '+')

                                            screenshotEntity = {'Image Name': f"{decodedPath} Screenshot {timeNow}",
                                                                'File Path': screenshotSavePath,
                                                                'Entity Type': 'Image'}
                                            try:
                                                page.screenshot(path=screenshotSavePath, full_page=True)
                                            except Error:
                                                try:
                                                    page.screenshot(path=screenshotSavePath, full_page=False)
                                                except Error:
                                                    screenshotEntity = {'Phrase': f'Could not take screenshot of '
                                                                                  f'{decodedPath}',
                                                                        'Entity Type': 'Phrase'}

                                            returnResults.append(
                                                [screenshotEntity,
                                                 {len(returnResults) + 1: {'Resolution': 'Screenshot of Tab',
                                                                           'Notes': ''}}])
                            else:
                                newEntity = [{'Phrase': actualURL,
                                              'Entity Type': 'Phrase'}]
                            if len(tabToOpen) == 3:
                                if historyMark != -1 and not tabToOpen[2]:
                                    newEntity.append({historyMark: {'Resolution': 'Next Page'}})
                                historyMark = len(returnResults)
                            returnResults.append(newEntity)
                    else:
                        self.mainWindow.warningSignalListener.emit('No Firefox session detected. Skipping importing '
                                                                   'from Firefox.', True)
                    browser.close()
                except Error as e:
                    self.mainWindow.warningSignalListener.emit(f'Cannot import tabs from Firefox: {str(repr(e))}', True)

            if self.importDialog.chromeChoice.isChecked() and not self.cancelled:
                progressValue = 2
                self.progressSignal.emit(progressValue)

                try:
                    browser = p.chromium.launch(executable_path=self.mainWindow.getPlaywrightBrowserPath('chromium'))

                    # NOTE: Cookies are not obtained for chromium based browsers.

                    if platform.system() == 'Linux':
                        context = browser.new_context(
                            viewport={'width': 1920, 'height': 1080},
                            user_agent=user_agents['Chrome']['Linux'][0]
                        )
                        sessionFilePath = Path.home() / '.config' / 'google-chrome' / 'Default' / 'Sessions'
                        if not sessionFilePath.exists():
                            sessionFilePath = Path.home() / 'snap' / 'chromium' / 'common' / 'chromium' / \
                                              'Default' / 'Sessions'
                    else:  # We already checked before that the platform is either 'Linux' or 'Windows'.
                        context = browser.new_context(
                            viewport={'width': 1920, 'height': 1080},
                            user_agent=user_agents['Chrome']['Windows'][0]
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
                                sessionFilePath = sessionFilePath.joinpath(f"Session_{latestTimestamp}")
                                chromeSessionFileContents = sessionFilePath.read_bytes()
                                break
                            except (FileNotFoundError, IndexError):
                                pass
                            except ValueError:
                                # No session files means we can't do anything for chrome.
                                break

                    if chromeSessionFileContents is None:
                        self.mainWindow.warningSignalListener.emit('Chrome / Chromium session file does not exist or '
                                                                   'is inaccessible. Cannot import tabs from '
                                                                   'Chrome / Chromium.', True)
                    else:
                        projectFilesDir = Path(self.mainWindow.SETTINGS.value("Project/FilesDir"))

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
                            if self.cancelled:
                                break
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

                                if self.importDialog.importScreenshotsCheckbox.isChecked():
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
                                        screenshotSavePath = screenshotSavePath.replace('\\', '+')
                                        page.screenshot(path=screenshotSavePath, full_page=True)

                                        returnResults.append(
                                            [{'Image Name': f"{decodedPath} Screenshot {timeNow}",
                                              'File Path': screenshotSavePath,
                                              'Entity Type': 'Image'},
                                             {len(returnResults) - 1: {'Resolution': 'Screenshot of Tab',
                                                                       'Notes': ''}}])

                    browser.close()
                except Error:
                    self.mainWindow.warningSignalListener.emit('Chrome / Chromium executable is not installed. Cannot '
                                                               'import tabs from Chrome / Chromium.', True)

        if self.cancelled:
            self.mainWindow.statusBarSignalListener.emit('Cancelled importing entities from Browser.')
        else:
            progressValue = 3
            self.progressSignal.emit(progressValue)
            self.menuObject.browserTabsImportDoneSignalListener.emit(
                returnResults,
                self.importDialog.importToCanvasDropdown.currentText() if
                self.importDialog.importToCanvasCheckbox.isChecked() else '')


class ImportTorBrowserTabsThread(QtCore.QThread):
    progressSignal = QtCore.Signal(int)
    cancelled = False

    def __init__(self, importDialog: TORBrowserImportDialog, mainWindowObject, menuObject):
        super(ImportTorBrowserTabsThread, self).__init__(parent=mainWindowObject)
        self.importDialog = importDialog
        self.mainWindow = mainWindowObject
        self.menuObject = menuObject

    def cancelOperation(self):
        self.cancelled = True

    def run(self) -> None:

        progressValue = 1
        self.progressSignal.emit(progressValue)

        returnResults = []

        torBrowserProfilePath = Path(self.mainWindow.SETTINGS.value("Program/TOR Profile Location", "/"))
        tabsFilePath = torBrowserProfilePath / 'sessionstore-backups' / 'recovery.jsonlz4'
        if not tabsFilePath.exists():
            progressValue = 4
            self.progressSignal.emit(progressValue)
            self.menuObject.browserTabsImportDoneSignalListener.emit(
                returnResults,
                '')
            return
        if self.importDialog.entireSessionChoice.isChecked():
            tabsToOpen = []
        else:
            tabsToOpen = set()

        tabsBytes = tabsFilePath.read_bytes()
        if tabsBytes[:8] == b'mozLz40\0':
            tabsBytes = lz4.block.decompress(tabsBytes[8:])
        tabsJson = json.loads(tabsBytes)
        for browserWindow in tabsJson['windows']:
            for browserTab in browserWindow['tabs']:
                if self.importDialog.entireSessionChoice.isChecked():
                    first = True
                    for browserEntry in browserTab['entries']:
                        url = browserEntry['url']
                        title = browserEntry.get('title', '')
                        if not url.startswith('about:'):
                            if first:
                                tabsToOpen.append((url, title, True))
                                first = False
                            else:
                                tabsToOpen.append((url, title, False))
                else:
                    browserEntry = browserTab['entries'][browserTab['index'] - 1]
                    url = browserEntry['url']
                    if not url.startswith('about:'):
                        tabsToOpen.add((url, browserEntry['title']))

        cookiesDatabasePath = torBrowserProfilePath / 'cookies.sqlite'
        browserCookies = self.menuObject.firefoxCookiesHelper(cookiesDatabasePath)

        historyMark = -1
        for tabToOpen in tabsToOpen:
            if self.cancelled:
                break
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
                    newEntity = [{'Document Name': urlTitle,
                                  'File Path': urlPath,
                                  'Entity Type': 'Document'}]
                elif 'image' in pathType:
                    newEntity = [{'Image Name': urlTitle,
                                  'File Path': urlPath,
                                  'Entity Type': 'Image'}]
                elif 'video' in pathType:
                    newEntity = [{'Video Name': urlTitle,
                                  'File Path': urlPath,
                                  'Entity Type': 'Video'}]
                elif 'archive' in pathType:
                    newEntity = [{'Archive Name': urlTitle,
                                  'File Path': urlPath,
                                  'Entity Type': 'Archive'}]

            elif parsedURL.scheme.startswith('http'):
                if '.onion' in actualURL:
                    newEntity = [{'Onion URL': actualURL,
                                  'Entity Type': 'Onion Website'}]
                else:
                    newEntity = [{'URL': actualURL,
                                  'Entity Type': 'Website'}]
            else:
                newEntity = [{'Phrase': actualURL,
                              'Entity Type': 'Phrase'}]

            if len(tabToOpen) == 3:
                if historyMark != -1 and not tabToOpen[2]:
                    newEntity.append({historyMark: {'Resolution': 'Next Page'}})
                historyMark = len(returnResults)
            returnResults.append(newEntity)

        progressValue = 3
        self.progressSignal.emit(progressValue)
        if self.cancelled:
            self.mainWindow.statusBarSignalListener.emit('Cancelled importing entities from Browser.')
        else:
            newTabEntities = len(returnResults)
            for cookie in browserCookies:
                cookieParents = []
                cookieURI = cookie['domain'] + cookie['path']
                if cookieURI.startswith('.'):
                    cookieURI = cookieURI[1:]
                for index, tabEntity in enumerate(returnResults[:newTabEntities]):
                    for key, value in tabEntity[0].items():
                        if key != 'Entity Type' and cookieURI in value:
                            cookieParents.append(index)
                cookieEntity = cookie
                cookieEntity['Phrase'] = f'Cookie {uuid4()}'
                cookieEntity['Entity Type'] = 'Phrase'

                cookieParentDict: dict = {}
                for cookieParent in cookieParents:
                    cookieParentDict[cookieParent] = {'Resolution': 'Site Cookie', 'Notes': ''}

                cookieResult = [cookieEntity, cookieParentDict]
                returnResults.append(cookieResult)

            progressValue = 4
            self.progressSignal.emit(progressValue)
            self.menuObject.browserTabsImportDoneSignalListener.emit(
                returnResults,
                self.importDialog.importToCanvasDropdown.currentText() if
                self.importDialog.importToCanvasCheckbox.isChecked() else '')
