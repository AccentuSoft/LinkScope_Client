#!/usr/bin/env python3

# Load modules
import re
import sys
import tempfile
import threading
import time

import networkx as nx
from ast import literal_eval
from uuid import uuid4
from shutil import move
from inspect import getsourcefile
from os import listdir, access, R_OK, W_OK
from os.path import abspath, dirname
from msgpack import load
from pathlib import Path
from datetime import datetime
from typing import Union
from PySide6 import QtWidgets, QtGui, QtCore

from Core import MessageHandler, SettingsObject
from Core import ResourceHandler
from Core import ReportGeneration
from Core import EntityDB
from Core import ResolutionManager
from Core import URLManager
from Core import FrontendCommunicationsHandler
from Core.ResolutionManager import StringPropertyInput, FilePropertyInput, SingleChoicePropertyInput, \
    MultiChoicePropertyInput
from Core.Interface import CentralPane
from Core.Interface import DockBarOne, DockBarTwo, DockBarThree
from Core.Interface import ToolBarOne
from Core.Interface import MenuBar
from Core.Interface import Stylesheets
from Core.Interface.Entity import BaseNode, BaseConnector, GroupNode
from Core.PathHelper import is_path_exists_or_creatable_portable


# Main Window of Application
class MainWindow(QtWidgets.QMainWindow):
    facilitateResolutionSignalListener = QtCore.Signal(str, list)
    notifyUserSignalListener = QtCore.Signal(str, str, bool)

    # Redefining the function to adjust its signature.
    def centralWidget(self) -> Union[QtWidgets.QWidget, QtWidgets.QWidget, CentralPane.WorkspaceWidget]:
        return super(MainWindow, self).centralWidget()

    def getSettings(self) -> SettingsObject.SettingsObject:
        return self.SETTINGS

    # Duplicate and alter a group entity to make it
    def copyGroupEntity(self, existingGroupUID: str, targetCanvas: CentralPane.CanvasScene) -> Union[dict, None]:
        # Have to make a new group entity, so that ungrouping in one canvas doesn't delete the entity
        #   group in another.
        entityJSON = self.LENTDB.getEntity(existingGroupUID)
        # Dereference the list, so we don't have issues w/ the original Group Node.
        newChildren = [childUID for childUID in list(entityJSON['Child UIDs'])
                       if childUID not in targetCanvas.sceneGraph.nodes]
        # Don't create the entity if all the nodes in it already exist on the target canvas.
        if len(newChildren) == 0:
            return None
        newEntity = self.LENTDB.addEntity(
            {'Group Name': entityJSON['Group Name'] + ' Copy',
             'Child UIDs': newChildren,
             'Entity Type': 'EntityGroup'})
        newUID = newEntity['uid']

        # Need to re-create the links too
        for linkUID in self.LENTDB.getOutgoingLinks(entityJSON['uid']):
            newLinkJSON = dict(self.LENTDB.getLink(linkUID))
            newLinkJSON['uid'] = (newUID, linkUID[1])
            self.LENTDB.addLink(newLinkJSON)
        for linkUID in self.LENTDB.getIncomingLinks(entityJSON['uid']):
            newLinkJSON = dict(self.LENTDB.getLink(linkUID))
            newLinkJSON['uid'] = (linkUID[0], newUID)
            self.LENTDB.addLink(newLinkJSON)
        return newEntity

    # What happens when the software is closed
    def closeEvent(self, event) -> None:
        self.dockbarThree.logViewerUpdateThread.endLogging = True
        self.saveTimer.stop()
        # Save the window settings
        self.SETTINGS.setValue("MainWindow/Geometry", self.saveGeometry().data())
        self.SETTINGS.setValue("MainWindow/WindowState", self.saveState().data())
        if self.FCOM.isConnected():
            self.FCOM.close()
        self.SETTINGS.setValue("Project/Server/Project", "")
        self.saveProject()
        # Wait just a little for the logging thread to close.
        # We don't _have_ to do this, but it stops errors from popping up due to threads being rudely interrupted.
        while not self.dockbarThree.logViewerUpdateThread.isFinished():
            time.sleep(0.01)
        super(MainWindow, self).closeEvent(event)

    def saveProject(self) -> None:
        try:
            self.SETTINGS.save()
            self.LENTDB.save()
            self.centralWidget().tabbedPane.save()
            self.setStatus("Project Saved.", 3000)
            self.MESSAGEHANDLER.info('Project Saved')
        except Exception as e:
            errorMessage = "Could not Save Project: " + str(repr(e))
            self.MESSAGEHANDLER.error(errorMessage, exc_info=True)
            self.setStatus("Failed Saving Project.", 3000)
            self.MESSAGEHANDLER.info("Failed Saving Project " + self.SETTINGS.value("Project/Name", 'Untitled'))

    def autoSaveProject(self):
        try:
            self.SETTINGS.save()
            self.LENTDB.save()
            self.centralWidget().tabbedPane.save()
            self.setStatus("Project Autosaved.", 3000)
        except Exception:
            self.setStatus("Failed Autosaving Project " + self.SETTINGS.value("Project/Name", 'Untitled'))

    def saveAsProject(self) -> None:
        if len(self.resolutions) > 0:
            self.MESSAGEHANDLER.warning('Cannot Save As project while resolutions are running. Running resolutions: '
                                        + str(self.resolutions), popUp=True)
            return
        # Native file dialogs (at least on Ubuntu) return sandboxed paths in some occasions, which messes with the
        #   saving of the project, since we need to create a directory to save the project in.
        saveAsDialog = QtWidgets.QFileDialog()
        saveAsDialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
        saveAsDialog.setViewMode(QtWidgets.QFileDialog.List)
        saveAsDialog.setFileMode(QtWidgets.QFileDialog.AnyFile)
        saveAsDialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        saveAsDialog.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)
        saveAsDialog.setDirectory(str(Path.home()))

        saveAsExec = saveAsDialog.exec()
        if not saveAsExec:
            self.setStatus('Save As operation cancelled.')
            return
        fileName = saveAsDialog.selectedFiles()[0]
        newProjectPath = Path(fileName)
        # There is a limit to how long path names can be. This will not prevent all edge cases with nested files,
        #   since users can have files with absurdly long names, but it should be a reasonable precaution.
        if not is_path_exists_or_creatable_portable(str(newProjectPath)):
            self.MESSAGEHANDLER.error(
                'Invalid project name or path to save at.', popUp=True, exc_info=False)
            return

        try:
            newProjectPath.mkdir(0o700, parents=False, exist_ok=False)
        except FileExistsError:
            self.MESSAGEHANDLER.error('Cannot save project to an existing directory. Please choose a unique name.',
                                      popUp=True, exc_info=False)
            return
        except FileNotFoundError:
            self.MESSAGEHANDLER.error('Cannot save project into a non-existing parent directory.'
                                      'Please create the required parent directories and try again.',
                                      popUp=True, exc_info=False)
            return

        oldName = self.SETTINGS.value("Project/Name")
        oldBaseDir = self.SETTINGS.value("Project/BaseDir")
        oldFilesDir = self.SETTINGS.value("Project/FilesDir")

        self.SETTINGS.setValue("Project/BaseDir", str(newProjectPath))
        self.SETTINGS.setValue("Project/FilesDir",
                               str(Path(self.SETTINGS.value("Project/BaseDir")).joinpath("Project Files")))
        self.SETTINGS.setValue("Project/Name", newProjectPath.name)

        try:
            Path(self.SETTINGS.value("Project/FilesDir")).mkdir(0o700, parents=False, exist_ok=False)
        except FileExistsError:
            self.MESSAGEHANDLER.error('Cannot save project to an existing directory. Please choose a unique name.',
                                      popUp=True, exc_info=False)
            self.SETTINGS.setValue("Project/BaseDir", oldBaseDir)
            self.SETTINGS.setValue("Project/FilesDir", oldFilesDir)
            self.SETTINGS.setValue("Project/Name", oldName)
            return
        except FileNotFoundError:
            self.MESSAGEHANDLER.error('Cannot save project into a non-existing parent directory.'
                                      'Please create the required parent directories and try again.',
                                      popUp=True, exc_info=False)
            self.SETTINGS.setValue("Project/BaseDir", oldBaseDir)
            self.SETTINGS.setValue("Project/FilesDir", oldFilesDir)
            self.SETTINGS.setValue("Project/Name", oldName)
            return

        self.setWindowTitle("LinkScope - " + self.SETTINGS.get('Project/Name', 'Untitled'))
        self.saveProject()
        self.setStatus('Project Saved As: ' + newProjectPath.name)

    # https://networkx.org/documentation/stable/reference/readwrite/graphml.html
    def exportCanvasToGraphML(self):
        currentCanvasGraph = self.centralWidget().tabbedPane.getCurrentScene().sceneGraph
        saveAsDialog = QtWidgets.QFileDialog()
        saveAsDialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
        saveAsDialog.setViewMode(QtWidgets.QFileDialog.List)
        saveAsDialog.setNameFilter("GraphML (*.xml)")
        saveAsDialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        saveAsDialog.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)
        saveAsDialog.setDirectory(str(Path.home()))

        if saveAsDialog.exec():
            try:
                filePath = saveAsDialog.selectedFiles()[0]
                if Path(filePath).suffix != '.xml':
                    filePath += '.xml'
                nx.write_graphml(currentCanvasGraph, filePath)
                self.setStatus('Canvas exported successfully.')
            except Exception as exc:
                self.MESSAGEHANDLER.error("Could not export canvas to file: " + str(exc), popUp=True)
                self.setStatus('Canvas export failed.')

    def importCanvasFromGraphML(self):
        openDialog = QtWidgets.QFileDialog()
        openDialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
        openDialog.setViewMode(QtWidgets.QFileDialog.List)
        openDialog.setNameFilter("GraphML (*.xml)")
        openDialog.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)
        openDialog.setDirectory(str(Path.home()))

        if openDialog.exec():
            filePath = openDialog.selectedFiles()[0]
            try:
                read_graphml = nx.read_graphml(filePath)
                currentScene = self.centralWidget().tabbedPane.getCurrentScene()
                # Deduplication, just in case.
                graphMLNodes = set(read_graphml.nodes())
                nodesToReadFirst = [self.LENTDB.getEntity(node) for node in graphMLNodes
                                    if not read_graphml.nodes[node].get('groupID')]
                nodesToReadFirst = [entity for entity in nodesToReadFirst if entity is not None and
                                    entity['Entity Type'] == 'EntityGroup']
                for entity in nodesToReadFirst:
                    # Create new group entity so we don't mess with the contents of the original.
                    if entity['uid'] not in currentScene.sceneGraph.nodes:
                        newGroupEntity = self.copyGroupEntity(entity['uid'], currentScene)
                        if newGroupEntity is not None:
                            currentScene.addNodeProgrammatic(newGroupEntity['uid'], newGroupEntity['Child UIDs'])
                    graphMLNodes.remove(entity['uid'])
                for node in graphMLNodes:
                    # Need to check as existing group nodes could have been updated with new nodes after export
                    #   but before the import.
                    if node not in currentScene.sceneGraph.nodes:
                        currentScene.addNodeProgrammatic(node)

                currentScene.rearrangeGraph()
                self.setStatus('Canvas imported successfully.')
            except KeyError:
                self.MESSAGEHANDLER.error("Aborted canvas import: One or more nodes in the graph "
                                          "do not exist in the database.", popUp=True)
                self.setStatus('Canvas import aborted.')
            except Exception as exc:
                self.MESSAGEHANDLER.error("Cannot import canvas: " + str(exc), popUp=True)
                self.setStatus('Canvas import failed.')

    def exportDatabaseToGraphML(self):
        # Need to create a new database to remove the icons
        self.LENTDB.dbLock.acquire()
        currentDatabase = nx.DiGraph(self.LENTDB.database)
        self.LENTDB.dbLock.release()

        for node in currentDatabase.nodes:
            # Remove icons. Will reset custom icons to default, but saves space.
            del currentDatabase.nodes[node]['Icon']
            if currentDatabase.nodes[node].get('Child UIDs'):
                currentDatabase.nodes[node]['Child UIDs'] = str(currentDatabase.nodes[node]['Child UIDs'])

        for edge in currentDatabase.edges:
            currentDatabase.edges[edge]['uid'] = str(currentDatabase.edges[edge]['uid'])

        saveAsDialog = QtWidgets.QFileDialog()
        saveAsDialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
        saveAsDialog.setViewMode(QtWidgets.QFileDialog.List)
        saveAsDialog.setNameFilter("GraphML (*.xml)")
        saveAsDialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        saveAsDialog.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)
        saveAsDialog.setDirectory(str(Path.home()))

        if saveAsDialog.exec():
            try:
                filePath = saveAsDialog.selectedFiles()[0]
                if Path(filePath).suffix != '.xml':
                    filePath += '.xml'
                nx.write_graphml(currentDatabase, filePath)
                self.setStatus('Database exported successfully.')
            except Exception as exc:
                self.MESSAGEHANDLER.error("Could not export database to file: " + str(exc), popUp=True)
                self.setStatus('Database export failed.')

    def importDatabaseFromGraphML(self):
        openDialog = QtWidgets.QFileDialog()
        openDialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
        openDialog.setViewMode(QtWidgets.QFileDialog.List)
        openDialog.setNameFilter("GraphML (*.xml)")
        openDialog.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)
        openDialog.setDirectory(str(Path.home()))

        if openDialog.exec():
            try:
                filePath = openDialog.selectedFiles()[0]
                read_graphml = nx.read_graphml(filePath)
                read_graphml_nodes = {key: read_graphml.nodes[key] for key in read_graphml.nodes}
                read_graphml_edges = {key: read_graphml.edges[key] for key in read_graphml.edges}
                for node in read_graphml_nodes:
                    read_graphml_nodes[node]['Icon'] = self.RESOURCEHANDLER.getEntityDefaultPicture(
                        read_graphml_nodes[node]['Entity Type'])
                    if read_graphml_nodes[node].get('Child UIDs'):
                        read_graphml_nodes[node]['Child UIDs'] = literal_eval(read_graphml_nodes[node]['Child UIDs'])
                for edge in read_graphml_edges:
                    read_graphml_edges[edge]['uid'] = literal_eval(read_graphml_edges[edge]['uid'])
                self.LENTDB.mergeDatabases(read_graphml_nodes, read_graphml_edges, fromServer=False)
                self.dockbarOne.existingEntitiesPalette.loadEntities()
                self.LENTDB.resetTimeline()
                self.setStatus('Database imported successfully.')
            except Exception as exc:
                self.MESSAGEHANDLER.error("Could not import database from file: " + str(exc), popUp=True)
                self.setStatus('Database import failed.')

    def generateReport(self):
        wizard = ReportWizard(self)
        wizard.show()

    def renameProjectPromptName(self) -> None:
        newName, confirm = QtWidgets.QInputDialog.getText(self,
                                                          'Rename Project',
                                                          'New Name:',
                                                          QtWidgets.QLineEdit.Normal,
                                                          text=self.SETTINGS.value("Project/Name"))
        if confirm:
            if newName == self.SETTINGS.value("Project/Name"):
                self.MESSAGEHANDLER.warning(
                    "New name must be different than current name.", popUp=True)
                return
            if newName == '':
                self.MESSAGEHANDLER.warning("New name cannot be blank.", popUp=True)
                return
            self.renameProject(newName)

    def renameProject(self, newName: str) -> None:
        if len(self.resolutions) > 0:
            self.MESSAGEHANDLER.warning('Cannot Rename project while resolutions are running. Running resolutions: '
                                        + str(self.resolutions), popUp=True)
            return
        oldName = self.SETTINGS.value("Project/Name")
        oldBaseDir = self.SETTINGS.value("Project/BaseDir")

        newBaseDir = Path(oldBaseDir).parent.joinpath(newName)

        if newBaseDir.exists():
            self.MESSAGEHANDLER.error('Path already exists.', popUp=True, exc_info=False)
            return

        if not is_path_exists_or_creatable_portable(str(newBaseDir)):
            self.MESSAGEHANDLER.error(
                'Invalid project name or path to save at.', popUp=True, exc_info=False)
            return

        self.SETTINGS.setValue("Project/BaseDir", str(newBaseDir))
        self.SETTINGS.setValue("Project/FilesDir",
                               str(Path(self.SETTINGS.value("Project/BaseDir")).joinpath("Project Files")))
        self.SETTINGS.setValue("Project/Name", newName)

        move(oldBaseDir, self.SETTINGS.value("Project/BaseDir"))
        oldProjectFile = newBaseDir.joinpath(oldName + '.linkscope')
        oldProjectFile.unlink(missing_ok=True)

        self.setWindowTitle("LinkScope - " + self.SETTINGS.get('Project/Name', 'Untitled'))
        self.saveProject()
        statusMessage = 'Project Renamed to: ' + newName
        self.setStatus(statusMessage)
        self.MESSAGEHANDLER.info(statusMessage)

    def addCanvas(self) -> None:
        # Create or open canvas
        connected = False
        if self.FCOM.isConnected():
            connected = True

        with self.syncedCanvasesLock:
            availableSyncedCanvases = self.syncedCanvases
        newCanvasPopup = CreateOrOpenCanvas(self, connected, availableSyncedCanvases)
        if newCanvasPopup.exec():
            self.MESSAGEHANDLER.info("New Canvas added: " + newCanvasPopup.canvasName)

    def toggleWorldDoc(self) -> None:
        if self.centralWidget() is not None:
            self.centralWidget().toggleLayout()

    def toggleLinkingMode(self) -> None:
        currentScene = self.centralWidget().tabbedPane.getCurrentScene()
        if currentScene.appendingToGroup:
            message = 'Cannot create manual link at this moment: Currently adding entities to group.'
            self.MESSAGEHANDLER.info(message, popUp=True)
            self.setStatus(message)
            return
        if self.linkingNodes:
            self.centralWidget().tabbedPane.enableAllTabs()
            currentScene.linking = False
            self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
            self.linkingNodes = False
        else:
            self.centralWidget().tabbedPane.disableAllTabsExceptCurrent()
            currentScene.linking = True
            currentScene.itemsToLink = []
            currentScene.clearSelection()
            self.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
            self.linkingNodes = True

    def deleteSpecificEntity(self, itemUID: str) -> None:
        self.centralWidget().tabbedPane.nodeRemoveAllHelper(itemUID)
        self.LENTDB.removeEntity(itemUID)
        self.MESSAGEHANDLER.info("Deleted node: " + itemUID)

    def deleteSpecificLink(self, linkUIDs: set) -> None:
        """
        Remove a set of connections between two nodes. This takes as an argument the set of link UIDs to remove
          (i.e. {(uid, uid), ...}) and it removes them from all canvases.
        :param linkUIDs: A list of link uid tuples to delete.
        :return:
        """
        linkUIDs = list(linkUIDs)
        for canvas in self.centralWidget().tabbedPane.canvasTabs:
            scene = self.centralWidget().tabbedPane.canvasTabs[canvas].scene()
            for linkUID in linkUIDs:
                scene.removeUIDFromLink(linkUID)
        for linkUID in linkUIDs:
            self.LENTDB.removeLink(linkUID)
            self.MESSAGEHANDLER.info("Deleted link: " + str(linkUID))

    def setGroupAppendMode(self, enable: bool) -> None:
        if self.centralWidget().tabbedPane.getCurrentScene().linking:
            message = 'Cannot append to group: Currently creating new link.'
            self.setStatus(message)
            self.MESSAGEHANDLER.info(message, popUp=True)
            return
        if enable:
            self.centralWidget().tabbedPane.disableAllTabsExceptCurrent()
            self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        else:
            self.centralWidget().tabbedPane.enableAllTabs()
            self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))

    def selectLeafNodes(self) -> None:
        """
        Select the nodes with at least one link coming into them, and no outgoing links.
            (i.e. They are a child node in at least 1 relationship, but are not a parent node in any relationship.)
        :return:
        """
        self.centralWidget().tabbedPane.getCurrentScene().clearSelection()
        currentCanvasGraph = self.centralWidget().tabbedPane.getCurrentScene().sceneGraph
        leaves = [x for x in currentCanvasGraph.nodes()
                  if currentCanvasGraph.out_degree(x) == 0 and currentCanvasGraph.in_degree(x) >= 1]
        for item in [node for node in self.centralWidget().tabbedPane.getCurrentScene().items()
                     if isinstance(node, BaseNode)]:
            if item.uid in leaves:
                item.setSelected(True)

    def selectRootNodes(self) -> None:
        """
        Select all the nodes that have at least one link going out of them, and no incoming links.
            (i.e. They are a parent node in at least 1 relationship, but are not a child node in any relationship.)
        :return:
        """
        self.centralWidget().tabbedPane.getCurrentScene().clearSelection()
        currentCanvasGraph = self.centralWidget().tabbedPane.getCurrentScene().sceneGraph
        roots = [x for x in currentCanvasGraph.nodes()
                 if currentCanvasGraph.out_degree(x) >= 1 and currentCanvasGraph.in_degree(x) == 0]
        for item in [node for node in self.centralWidget().tabbedPane.getCurrentScene().items()
                     if isinstance(node, BaseNode)]:
            if item.uid in roots:
                item.setSelected(True)

    def selectIsolatedNodes(self) -> None:
        """
        Select all the nodes that have no links coming into or going out of them.
        :return:
        """
        self.centralWidget().tabbedPane.getCurrentScene().clearSelection()
        currentCanvasGraph = self.centralWidget().tabbedPane.getCurrentScene().sceneGraph
        nodes = [x for x in currentCanvasGraph.nodes()
                 if currentCanvasGraph.out_degree(x) == 0 and currentCanvasGraph.in_degree(x) == 0]
        for item in [node for node in self.centralWidget().tabbedPane.getCurrentScene().items()
                     if isinstance(node, BaseNode)]:
            if item.uid in nodes:
                item.setSelected(True)

    def selectNonIsolatedNodes(self) -> None:
        """
        Select all nodes with at least one link going into or out of them.
        :return:
        """
        self.centralWidget().tabbedPane.getCurrentScene().clearSelection()
        currentCanvasGraph = self.centralWidget().tabbedPane.getCurrentScene().sceneGraph
        nodes = [x for x in currentCanvasGraph.nodes()
                 if currentCanvasGraph.out_degree(x) > 0 or currentCanvasGraph.in_degree(x) > 0]
        for item in [node for node in self.centralWidget().tabbedPane.getCurrentScene().items()
                     if isinstance(node, BaseNode)]:
            if item.uid in nodes:
                item.setSelected(True)

    def findShortestPath(self) -> None:
        """
        Find the shortest path between two nodes, if it exists.
        Exactly two nodes must be selected.
        :return:
        """
        endPoints = [item.uid for item in self.centralWidget().tabbedPane.getCurrentScene().selectedItems()
                     if isinstance(item, BaseNode)]
        if len(endPoints) != 2:
            self.MESSAGEHANDLER.warning('Exactly two entities must be selected for the Shortest Path function to work.',
                                        popUp=True)
            return
        currentCanvasGraph = self.centralWidget().tabbedPane.getCurrentScene().sceneGraph
        try:
            shortestPath = nx.shortest_path(currentCanvasGraph, endPoints[0], endPoints[1])
        except nx.NetworkXNoPath:
            try:
                shortestPath = nx.shortest_path(currentCanvasGraph, endPoints[1], endPoints[0])
            except nx.NetworkXNoPath:
                shortestPath = None

        if shortestPath is None:
            messagePathNotFound = 'No path found connecting the selected nodes: ' + str(endPoints)
            self.setStatus(messagePathNotFound)
            self.MESSAGEHANDLER.info(messagePathNotFound, popUp=True)
        else:
            self.centralWidget().tabbedPane.getCurrentScene().clearSelection()
            for item in [node for node in self.centralWidget().tabbedPane.getCurrentScene().items()
                         if isinstance(node, BaseNode)]:
                if item.uid in shortestPath:
                    item.setSelected(True)
            linksToSelect = [(a, b) for a, b in zip(shortestPath, shortestPath[1:])]
            for linkItem in [link for link in self.centralWidget().tabbedPane.getCurrentScene().items()
                             if isinstance(link, BaseConnector)]:
                if linkItem.uid.intersection(linksToSelect):
                    linkItem.setSelected(True)
            self.setStatus('Shortest path found.')

    def findEntityOrLinkOnCanvas(self, regex: bool = False) -> None:
        currentScene = self.centralWidget().tabbedPane.getCurrentScene()
        currentUIDs = [item.uid for item in currentScene.items() if isinstance(item, BaseNode)
                       or isinstance(item, BaseConnector)]
        entityPrimaryFields = {}
        for uid in currentUIDs:
            if isinstance(uid, str):
                item = self.LENTDB.getEntity(uid)
                if item is not None:
                    if not entityPrimaryFields.get(item[list(item)[1]]):
                        entityPrimaryFields[item[list(item)[1]]] = set()
                    entityPrimaryFields[item[list(item)[1]]].add(uid)

            elif isinstance(uid, set):
                for potentialLinkItem in uid:
                    item = self.LENTDB.getLink(potentialLinkItem)
                    if item is not None:
                        if not entityPrimaryFields.get(item['Resolution']):
                            entityPrimaryFields[item['Resolution']] = set()
                        entityPrimaryFields[item['Resolution']].add(str(uid))
        findPrompt = FindEntityOnCanvasDialog(list(entityPrimaryFields), regex)

        if findPrompt.exec():
            uidsToSelect = []
            findText = findPrompt.findInput.text()
            if findText != "":
                try:
                    if regex:
                        expression = re.compile(findText)
                        for item in entityPrimaryFields:
                            if expression.match(item):
                                # Add the elements in each index to uidsToSelect instead of the sets themselves.
                                uidsToSelect.extend(entityPrimaryFields[item])

                    else:
                        for item in entityPrimaryFields:
                            if item.startswith(findText):
                                # Add the elements in each index to uidsToSelect instead of the sets themselves.
                                uidsToSelect.extend(entityPrimaryFields[item])

                    currentScene.clearSelection()
                    for item in [linkOrEntity for linkOrEntity in currentScene.items()
                                 if isinstance(linkOrEntity, BaseNode) or isinstance(linkOrEntity, BaseConnector)]:
                        if str(item.uid) in uidsToSelect:
                            item.setSelected(True)
                    if len(uidsToSelect) == 1 and ',' not in uidsToSelect[0]:
                        self.centralWidget().tabbedPane.getCurrentView().centerViewportOnNode(uidsToSelect[0])
                except re.error:
                    self.MESSAGEHANDLER.error('Invalid Regex Specified!', popUp=True, exc_info=False)

    def findEntityOfTypeOnCanvas(self, regex: bool = False) -> None:
        currentScene = self.centralWidget().tabbedPane.getCurrentScene()
        currentUIDs = [item.uid for item in currentScene.items() if isinstance(item, BaseNode)]
        # Keys: Entity Types. Values: dicts, where the key is the primary field and the value is the UID.
        entityTypesOnCanvas = {}
        for uid in currentUIDs:
            item = self.LENTDB.getEntity(uid)
            if item is not None:
                itemType = item.get('Entity Type')
                itemPrimaryFieldValue = item[self.RESOURCEHANDLER.getPrimaryFieldForEntityType(itemType)]
                if itemType not in entityTypesOnCanvas:
                    entityTypesOnCanvas[itemType] = {}
                if itemPrimaryFieldValue not in entityTypesOnCanvas[itemType]:
                    entityTypesOnCanvas[itemType][itemPrimaryFieldValue] = set()
                entityTypesOnCanvas[itemType][itemPrimaryFieldValue].add(uid)

        findPrompt = FindEntityOfTypeOnCanvasDialog(entityTypesOnCanvas, regex)

        if findPrompt.exec():
            uidsToSelect = []
            findText = findPrompt.findInput.text()
            findType = findPrompt.typeInput.currentText()
            if findText != "":
                try:
                    if regex:
                        expression = re.compile(findText)
                        for item in entityTypesOnCanvas[findType]:
                            if expression.match(item):
                                # Add the elements in each index to uidsToSelect instead of the sets themselves.
                                uidsToSelect.extend(entityTypesOnCanvas[findType][item])

                    else:
                        for item in entityTypesOnCanvas[findType]:
                            if item.startswith(findText):
                                # Add the elements in each index to uidsToSelect instead of the sets themselves.
                                uidsToSelect.extend(entityTypesOnCanvas[findType][item])

                    currentScene.clearSelection()
                    for item in [sceneEntity for sceneEntity in currentScene.items()
                                 if isinstance(sceneEntity, BaseNode)]:
                        if item.uid in uidsToSelect:
                            item.setSelected(True)
                    if len(uidsToSelect) == 1:
                        self.centralWidget().tabbedPane.getCurrentView().centerViewportOnNode(uidsToSelect[0])
                except re.error:
                    self.MESSAGEHANDLER.error('Invalid Regex Specified!', popUp=True, exc_info=False)

    def findResolution(self) -> None:
        # Dereference the entities and resolutions, just to be safe.
        findDialog = FindResolutionDialog(self, list(self.RESOURCEHANDLER.getAllEntities()),
                                          dict(self.RESOLUTIONMANAGER.resolutions))
        findDialog.exec()

    def mergeEntities(self) -> None:
        """
        Show table of entities w/ primary fields, and incoming / outgoing links.
        Let user choose which entity should be the primary one. For all the rest:
            Get all links to and from them, and add them to the primary one.
            Add their fields to the primary one, if they are not the same.
            Delete them when done.
        :return:
        """
        entitiesToMerge = [self.LENTDB.getEntity(item.uid)
                           for item in self.centralWidget().tabbedPane.getCurrentScene().selectedItems()
                           if isinstance(item, BaseNode) and not isinstance(item, GroupNode)]
        if len(entitiesToMerge) < 2:
            self.MESSAGEHANDLER.info('Not enough valid entities to merge selected! Please choose at least two'
                                     ' non-Meta entities.', popUp=True)
            return
        mergeDialog = MergeEntitiesDialog(self, entitiesToMerge)

        if mergeDialog.exec():
            primaryEntityUID = mergeDialog.primaryEntityUID
            primaryEntity = [entity for entity in entitiesToMerge if entity['uid'] == primaryEntityUID][0]
            otherEntitiesUIDs = mergeDialog.otherEntitiesUIDs  # First entity is written first. No overwrites.
            allParentsPrimary = [link[0] for link in self.LENTDB.getIncomingLinks(primaryEntityUID)]
            allChildrenPrimary = [link[1] for link in self.LENTDB.getOutgoingLinks(primaryEntityUID)]
            # Do not want links pointing to itself.
            allParentsPrimary.append(primaryEntityUID)
            allChildrenPrimary.append(primaryEntityUID)
            linksToAdd = []

            for entityUID in otherEntitiesUIDs:
                otherEntity = [otherEntity for otherEntity in entitiesToMerge if otherEntity['uid'] == entityUID][0]
                # Do not include links to / from entities where such links exist already on the primary entity.
                # Also do not include links to / from other entities that are being merged.
                allIncomingLinks = [link for link in self.LENTDB.getIncomingLinks(entityUID)
                                    if link[0] not in allParentsPrimary and
                                    link[0] not in otherEntitiesUIDs]
                allOutgoingLinks = [link for link in self.LENTDB.getOutgoingLinks(entityUID)
                                    if link[1] not in allChildrenPrimary
                                    and link[1] not in otherEntitiesUIDs]
                for field in otherEntity:
                    # Check if field does not exist, or if it does, but contains 'None' value.
                    if str(primaryEntity.get(field)) == 'None':
                        primaryEntity[field] = otherEntity[field]
                for incomingLink in allIncomingLinks:
                    linkJson = self.LENTDB.getLink(incomingLink)
                    linksToAdd.append([incomingLink[0], primaryEntity['uid'], linkJson['Resolution'],
                                       linkJson['Notes']])
                for outgoingLink in allOutgoingLinks:
                    linkJson = self.LENTDB.getLink(outgoingLink)
                    linksToAdd.append([primaryEntity['uid'], outgoingLink[1], linkJson['Resolution'],
                                       linkJson['Notes']])
                self.deleteSpecificEntity(entityUID)
            self.centralWidget().tabbedPane.linkAddHelper(linksToAdd)

    def splitEntity(self) -> None:
        entityToSplit = [self.LENTDB.getEntity(item.uid)
                         for item in self.centralWidget().tabbedPane.getCurrentScene().selectedItems()
                         if isinstance(item, BaseNode)]
        validEntityToSplit = [entity for entity in entityToSplit
                              if entity['Entity Type'] != 'EntityGroup']
        if len(validEntityToSplit) == 0:
            self.MESSAGEHANDLER.info('No valid entities to split selected! Please choose at least one non-Meta entity.',
                                     popUp=True)
            return
        elif len(validEntityToSplit) > 1:
            self.MESSAGEHANDLER.info('Multiple entities selected. Please pick one valid entity to split.',
                                     popUp=True)
            return

        entityToSplit = validEntityToSplit[0]
        entityToSplitPrimaryFieldKey = list(entityToSplit)[1]
        entityToSplitUID = entityToSplit['uid']
        splitDialog = SplitEntitiesDialog(self, entityToSplit)

        if splitDialog.exec():
            canvasTabs = self.centralWidget().tabbedPane.canvasTabs
            allScenesWithNode = [canvasTabs[view].scene() for view in canvasTabs
                                 if entityToSplitUID in canvasTabs[view].scene().sceneGraph.nodes()]
            for newEntityWithLinks in splitDialog.splitEntitiesWithLinks:
                newEntity = {entityToSplitPrimaryFieldKey: newEntityWithLinks[0]}
                for field in entityToSplit:
                    if field != 'uid' and field != entityToSplitPrimaryFieldKey:
                        newEntity[field] = entityToSplit[field]
                newEntity = self.LENTDB.addEntity(newEntity)

                for link in newEntityWithLinks[1]:
                    newLink = {}
                    for field in link:
                        newLink[field] = link[field]
                    if newLink['uid'][0] == entityToSplitUID:
                        newLink['uid'] = (newEntity['uid'], newLink['uid'][1])
                    else:
                        newLink['uid'] = (newLink['uid'][0], newEntity['uid'])
                    self.LENTDB.addLink(newLink)
                for scene in allScenesWithNode:
                    scene.addNodeProgrammatic(newEntity['uid'])
            self.deleteSpecificEntity(entityToSplitUID)
            for scene in allScenesWithNode:
                scene.rearrangeGraph()

    def handleGroupNodeUpdateAfterEntityDeletion(self, entityUID) -> None:
        for canvas in self.centralWidget().tabbedPane.canvasTabs:
            self.centralWidget().tabbedPane.canvasTabs[canvas].cleanDeletedNodeFromGroupsIfExists(entityUID)

    def editProjectSettings(self) -> None:
        settingsDialog = ProjectEditDialog(self.SETTINGS)
        settingsConfirm = settingsDialog.exec()

        if settingsConfirm:
            # Save new settings
            newSettings = settingsDialog.newSettings
            for key in newSettings:
                newSettingValue = newSettings[key]
                if newSettingValue[1]:
                    # Delete key
                    self.SETTINGS.pop(key)
                elif newSettingValue[0] != '':
                    # Do not allow blank settings.
                    if key == 'Project/Resolution Result Grouping Threshold' or \
                            key == 'Project/Number of Answers Returned' or \
                            key == 'Project/Question Answering Retriever Value' or \
                            key == 'Project/Question Answering Reader Value':
                        try:
                            int(newSettingValue[1])
                            self.SETTINGS.setValue(key, newSettingValue[0])
                        except ValueError:
                            pass
                    elif newSettingValue[0] == 'Copy' or newSettingValue[0] == 'Symlink':
                        self.SETTINGS.setValue(key, newSettingValue[0])

            self.saveProject()

    def editResolutionsSettings(self) -> None:
        settingsDialog = ResolutionsEditDialog(self.SETTINGS)
        settingsConfirm = settingsDialog.exec()

        if settingsConfirm:
            # Save new settings
            newSettings = settingsDialog.newSettings
            for key in newSettings:
                newSettingValue = newSettings[key]
                if newSettingValue[1]:
                    # Delete key
                    self.SETTINGS.pop(key)
                elif newSettingValue[0] != '':
                    # Do not allow blank settings.
                    self.SETTINGS.setValue(key, newSettingValue[0])

            self.saveProject()

    def editLogSettings(self) -> None:
        settingsDialog = LoggingSettingsDialog(self.SETTINGS)
        settingsConfirm = settingsDialog.exec()

        if settingsConfirm:
            # Save new settings
            newSettings = settingsDialog.newSettings
            for key in newSettings:
                newSettingValue = newSettings[key]
                if newSettingValue[1]:
                    # Delete key
                    self.SETTINGS.pop(key)
                elif newSettingValue[0] != '':
                    # Do not allow blank settings.
                    self.SETTINGS.setValue(key, newSettingValue[0])

            self.MESSAGEHANDLER.setSeverityLevel(self.SETTINGS.value('Logging/Severity'))
            self.MESSAGEHANDLER.changeLogfile(self.SETTINGS.value('Logging/Logfile'))
            self.saveProject()

    def editProgramSettings(self) -> None:
        settingsDialog = ProgramEditDialog(self.SETTINGS)
        settingsConfirm = settingsDialog.exec()

        if settingsConfirm:
            # Save new settings
            newSettings = settingsDialog.newSettings
            for key in newSettings:
                newSettingValue = newSettings[key]
                if newSettingValue[1]:
                    # Delete key
                    self.SETTINGS.pop(key)
                elif newSettingValue[0] != '':
                    # Do not allow blank settings.
                    self.SETTINGS.setValue(key, newSettingValue[0])

            self.saveProject()

    def changeGraphics(self) -> None:
        settingsDialog = GraphicsEditDialog(self.SETTINGS, self.RESOURCEHANDLER)
        settingsConfirm = settingsDialog.exec()

        if settingsConfirm:
            newSettings = settingsDialog.newSettings
            try:
                etfVal = int(newSettings["ETF"])
                self.entityTextFont.setPointSize(etfVal)
                self.SETTINGS.setValue("Program/EntityTextFontSize", str(newSettings["ETF"]))
            except ValueError:
                pass
            try:
                ltfVal = int(newSettings["LTF"])
                self.linkTextFont.setPointSize(ltfVal)
                self.SETTINGS.setValue("Program/LinkTextFontSize", str(newSettings["LTF"]))
            except ValueError:
                pass

            etcVal = newSettings["ETC"]
            newEtcColor = QtGui.QColor(etcVal)
            if newEtcColor.isValid():
                self.entityTextBrush.setColor(newEtcColor)
                self.SETTINGS.setValue("Program/EntityTextColor", newEtcColor.name())
            ltcVal = newSettings["LTC"]
            newLtcColor = QtGui.QColor(ltcVal)
            if newLtcColor.isValid():
                self.linkTextBrush.setColor(newLtcColor)
                self.SETTINGS.setValue("Program/LinkTextColor", newLtcColor.name())

            for viewKey in self.centralWidget().tabbedPane.canvasTabs:
                scene = self.centralWidget().tabbedPane.canvasTabs[viewKey].scene()
                scene.updateNodeGraphics(self.entityTextFont, self.entityTextBrush, self.linkTextFont,
                                         self.linkTextBrush)

            self.saveProject()

    def loadModules(self) -> None:
        """
        Loads user-defined modules from the Modules folder in the installation directory.
        :return:
        """
        self.RESOURCEHANDLER.loadModuleEntities()
        modulesBasePath = Path(self.SETTINGS.value("Program/BaseDir")).joinpath("Modules")
        for module in listdir(modulesBasePath):
            self.RESOLUTIONMANAGER.loadResolutionsFromDir(modulesBasePath / module)
        self.setStatus('Loaded Modules.')

    def reloadModules(self) -> None:
        """
        Same as loadModules, except this one updates the GUI to show newly loaded entities and resolutions.
        This is meant to be ran after the application started, in case the user wants to load a module without
        closing and reopening the application.
        :return:
        """
        self.RESOURCEHANDLER.loadModuleEntities()
        modulesBasePath = Path(self.SETTINGS.value("Program/BaseDir")).joinpath("Modules")
        for module in listdir(modulesBasePath):
            self.RESOLUTIONMANAGER.loadResolutionsFromDir(modulesBasePath / module)
        self.dockbarOne.existingEntitiesPalette.loadEntities()
        self.dockbarOne.resolutionsPalette.loadAllResolutions()
        self.dockbarOne.nodesPalette.loadEntities()
        self.setStatus('Reloaded Modules.')

    def setStatus(self, message: str, timeout: int = 5000) -> None:
        """
        Show the message provided in the status bar.
        Timeout dictates how long the message is shown, in milliseconds.

        Translates the message automatically, no need to call 'tr' on the message parameter used.
        """

        self.statusBar().showMessage(self.tr(message), timeout)

    def notifyUser(self, message: str, title: str = "LinkScope Notification", beep: bool = True,
                   icon: QtGui.QIcon = None) -> None:
        if icon is not None:
            self.trayIcon.showMessage(self.tr(title), self.tr(message), icon)
        else:
            self.trayIcon.showMessage(self.tr(title), self.tr(message))
        if beep:
            application.beep()

    def getPictureOfCanvas(self, canvasName: str, justViewport: bool = True,
                           transparentBackground: bool = False) -> Union[QtGui.QPicture, None]:
        view = self.centralWidget().tabbedPane.canvasTabs.get(canvasName)
        if view is None:
            return None
        return view.takePictureOfView(justViewport, transparentBackground)

    def resetTimeline(self, graph: nx.DiGraph) -> None:
        self.dockbarThree.timeWidget.resetTimeline(graph, True)

    def updateTimeline(self, node, added: bool = True, updateGraph: bool = True) -> None:
        self.dockbarThree.timeWidget.updateTimeline(node, added, updateGraph)

    def timelineSelectMatchingEntities(self, timescale: list) -> None:
        if not timescale:  # i.e. if timescale == []
            return
        scene = self.centralWidget().tabbedPane.getCurrentScene()
        scene.clearSelection()
        for uid in scene.nodesDict:
            if self.LENTDB.isNode(uid):
                createdDate = datetime.fromisoformat(self.LENTDB.getEntity(uid)['Date Created'])
                try:
                    year = timescale[0]
                except IndexError:
                    year = None
                try:
                    month = timescale[1]
                except IndexError:
                    month = None
                try:
                    day = timescale[2]
                except IndexError:
                    day = None
                try:
                    hour = timescale[3]
                except IndexError:
                    hour = None
                try:
                    minute = timescale[4]
                except IndexError:
                    minute = None

                if minute is not None and createdDate.minute != minute:
                    continue
                if hour is not None and createdDate.hour != hour:
                    continue
                if day is not None and createdDate.day != day:
                    continue
                if month is not None and createdDate.month != month:
                    continue
                if year is not None and createdDate.year != year:
                    continue

                scene.nodesDict[uid].setSelected(True)

    def setCurrentCanvasSelection(self, uidList: list) -> None:
        currScene = self.centralWidget().tabbedPane.getCurrentScene()
        currScene.clearSelection()
        for item in uidList:
            if isinstance(item, str):
                nodeItem = currScene.getVisibleNodeForUID(item)
                if nodeItem is not None:
                    nodeItem.setSelected(True)
            else:
                linkItem = currScene.getVisibleLinkForUID(item)
                if linkItem is not None:
                    linkItem.setSelected(True)
                else:
                    for entityItem in item:
                        nodeItem = currScene.getVisibleNodeForUID(entityItem)
                        if nodeItem is not None:
                            nodeItem.setSelected(True)
        if len(uidList) == 1 and isinstance(uidList[0], str):
            self.centralWidget().tabbedPane.getCurrentView().centerViewportOnNode(uidList[0])

    def populateDetailsWidget(self, uids) -> None:
        eJson = []
        for uid in uids:
            # Connectors give the list if edge UIDs they represent
            if isinstance(uid, set):
                for linkUID in uid:
                    eJson.append(self.LENTDB.getLink(linkUID))
            else:
                eJson.append(self.LENTDB.getEntity(uid))

        self.dockbarTwo.entDetails.displayWidgetDetails(eJson)

    def updateEntityNodeLabelsOnCanvases(self, uid: str, label: str) -> None:
        """
        If an entity is updated (i.e. re-added) to the database, the labels
          for each node on each canvas need to be updated as well.

        :param label:
        :param uid:
        :return:
        """
        for tab in self.centralWidget().tabbedPane.canvasTabs:
            scene = self.centralWidget().tabbedPane.canvasTabs[tab].scene()
            try:
                scene.nodesDict[uid].updateLabel(label)
            except KeyError:
                pass

    def updateLinkLabelsOnCanvases(self, uid: str, label: str) -> None:
        """
        If a link is updated (i.e. re-added) to the database, the labels
          for each link label on each canvas need to be updated as well.

        :param label:
        :param uid:
        :return:
        """
        for tab in self.centralWidget().tabbedPane.canvasTabs:
            scene = self.centralWidget().tabbedPane.canvasTabs[tab].scene()
            try:
                scene.linksDict[uid].updateLabel(label)
            except KeyError:
                pass

    def populateEntitiesWidget(self, eJson: dict, add: bool) -> None:
        if add:
            self.dockbarOne.existingEntitiesPalette.addEntity(eJson)
        else:
            self.dockbarOne.existingEntitiesPalette.removeEntity(eJson)

    def populateResolutionsWidget(self, selected) -> None:
        self.dockbarOne.resolutionsPalette.loadResolutionsForSelected(selected)

    def runResolution(self, resolution) -> None:
        """
        Runs the specified resolution in another thread.
        """
        self.setStatus("Running Resolution: " + resolution)
        try:
            category, resolution = resolution.split('/')
        except ValueError:
            self.MESSAGEHANDLER.error('Category name or resolution name should not contain slashes: ' + resolution)
            return

        scene = self.centralWidget().tabbedPane.getCurrentScene()
        items = scene.selectedItems()
        resArgument = []
        for item in items:
            if not isinstance(item, BaseNode):
                continue
            resArgument.append(self.LENTDB.getEntity(item.uid))

        parameters = self.RESOLUTIONMANAGER.getResolutionParameters(category, resolution)
        if parameters is None:
            message = 'Resolution parameters not found for resolution: ' + resolution
            self.MESSAGEHANDLER.error(message, popUp=True, exc_info=False)
            self.setStatus(message)
            return

        resolutionParameterValues = {}
        resolutionUnspecifiedParameterValues = {}
        for parameter in parameters:
            if parameters[parameter].get('global') is True:
                # Extra slash in the middle to ensure that resolutions cannot overwrite these accidentally,
                #   since slashes are not allowed by default on Linux or Windows.
                savedParameterValue = self.SETTINGS.value('Resolutions/Global/Parameters/' + parameter)
            else:
                savedParameterValue = self.SETTINGS.value('Resolutions/' + resolution + '/' + parameter)
            if savedParameterValue is not None:
                resolutionParameterValues[parameter] = savedParameterValue
            else:
                resolutionUnspecifiedParameterValues[parameter] = parameters[parameter]

        # Show Resolution wizard if there are any parameters required that aren't saved in settings, or
        #   if the user did not select any items to run the resolution on.
        if len(items) == 0 or (0 < len(parameters) and 0 < len(resolutionUnspecifiedParameterValues)):
            selectEntityList = None
            uidAndPrimaryFields: list = []
            acceptableOriginTypes = None
            resolutionDescription = None
            if len(items) == 0:
                acceptableOriginTypes = self.RESOLUTIONMANAGER.getResolutionOriginTypes(resolution)
                uidAndPrimaryFields = [(entity['uid'], entity[list(entity)[1]])
                                       for entity in self.LENTDB.getAllEntities()
                                       if entity['Entity Type'] in acceptableOriginTypes]
                selectEntityList = [entity[1] for entity in uidAndPrimaryFields]
                resolutionDescription = self.RESOLUTIONMANAGER.getResolutionDescription(resolution)

            parameterSelector = ResolutionParametersSelector(
                resolutionUnspecifiedParameterValues, selectEntityList, acceptableOriginTypes, resolutionDescription)
            parameterSelectorConfirm = parameterSelector.exec()

            if not parameterSelectorConfirm:
                self.setStatus('Resolution ' + resolution + ' aborted.')
                return
            else:
                resolutionParameterValues.update(parameterSelector.chosenParameters)

                newParametersToSave = parameterSelector.parametersToRemember
                for parameterToRemember in newParametersToSave:
                    # No need to update settings objects here - these values are only relevant to the mainWindow,
                    #   since this function is where all the resolutions are ran from.
                    if parameters[parameterToRemember].get('global') is True:
                        self.SETTINGS.setValue('Resolutions/Global/Parameters/' + parameterToRemember,
                                               newParametersToSave[parameterToRemember])
                    else:
                        self.SETTINGS.setValue('Resolutions/' + resolution + '/' + parameterToRemember,
                                               newParametersToSave[parameterToRemember])

                if len(items) == 0:
                    selectedEntities = parameterSelector.entitySelector.selectedItems()
                    if len(selectedEntities) == 0:
                        self.setStatus('Resolution ' + resolution +
                                       ' did not run: No entities selected.')
                        return

                    for selectedEntity in selectedEntities:
                        uid = uidAndPrimaryFields[selectEntityList.index(selectedEntity.text())][0]
                        resArgument.append(self.LENTDB.getEntity(uid))

        resolutionParameterValues['Project Files Directory'] = self.SETTINGS.value("Project/FilesDir")
        resolutionUID = str(uuid4())
        resolutionThread = ResolutionExecutorThread(
            resolution, resArgument, resolutionParameterValues, self, resolutionUID)
        resolutionThread.sig.connect(self.resolutionSignalListener)
        resolutionThread.sigError.connect(self.resolutionErrorSignalListener)
        self.MESSAGEHANDLER.info('Running Resolution: ' + resolution)
        resolutionThread.start()
        self.resolutions.append((resolutionThread, category == 'Server Resolutions'))

    def resolutionSignalListener(self, resolution_name: str, resolution_result: Union[list, str]) -> None:
        """
        Is called by the threads created by runResolution to handle the
        result, i.e. run the function that adds nodes and links.
        """
        if isinstance(resolution_result, str):
            self.MESSAGEHANDLER.info(f"Resolution {resolution_name} finished with status: {resolution_result}",
                                     popUp=True)
        elif len(resolution_result) == 0:
            self.MESSAGEHANDLER.info(f"Resolution {resolution_name} returned no results.", popUp=True)
        else:
            self.centralWidget().tabbedPane.facilitateResolution(resolution_name, resolution_result)

        self.cleanUpLocalFinishedResolutions()
        self.setStatus("Resolution: " + resolution_name + " completed.")

    def resolutionErrorSignalListener(self, error_message: str):
        self.MESSAGEHANDLER.error(error_message, popUp=True)

    def cleanUpLocalFinishedResolutions(self) -> None:
        """
        Clean out old non-server resolutions.
        :return:
        """
        for resolutionThread in list(self.resolutions):
            if resolutionThread[0].isFinished() and resolutionThread[1] is False:
                self.resolutions.remove(resolutionThread)

    def getClientCollectors(self) -> dict:
        with self.serverCollectorsLock:
            try:
                clientCollectorUIDs = literal_eval(self.SETTINGS.value('Project/Server/Collectors'))
                if not isinstance(clientCollectorUIDs, dict):
                    raise ValueError('Collectors were not saved in the correct format.')
            except Exception as e:
                self.MESSAGEHANDLER.error('Unable to load Collectors from Settings file.',
                                          popUp=False,
                                          exc_info=False)
                self.MESSAGEHANDLER.debug('Cannot eval Project/Server/Collectors setting: ' + str(e))
                clientCollectorUIDs = {}
        return clientCollectorUIDs

    def setClientCollectors(self, newClientCollectorsDict: dict) -> None:
        if not isinstance(newClientCollectorsDict, dict):
            self.MESSAGEHANDLER.error('Unable to save Collectors to Settings: Invalid format.')
            self.MESSAGEHANDLER.debug('Collectors argument: ' + str(newClientCollectorsDict))
            self.MESSAGEHANDLER.debug('Collectors format: ' + str(type(newClientCollectorsDict)))
        else:
            with self.serverCollectorsLock:
                self.SETTINGS.setValue('Project/Server/Collectors', str(newClientCollectorsDict))
                self.SETTINGS.save()
            self.MESSAGEHANDLER.info('Client Collectors state updated.')

    def receiveCollectorResultListener(self, collector_name: str, collector_uid: str, timestamp: str, results: list):
        # Signal ints are 4 bytes long and signed, so we use strings to communicate timestamps.
        currentCollectors = self.getClientCollectors()
        currentCollectors[collector_uid] = int(timestamp)
        self.setClientCollectors(currentCollectors)
        self.centralWidget().tabbedPane.facilitateResolution('Collector ' + str(collector_uid), results)
        self.notifyUser("New entities discovered by collector: " + str(collector_name), "Collector Update")

    # Server functions
    def statusMessageListener(self, message: str, showPopup: bool = True) -> None:
        if showPopup:
            self.MESSAGEHANDLER.info(message, popUp=True)
        self.setStatus(message)

    def connectedToServerListener(self, server: str) -> None:
        self.setStatus("Connected to server: " + server)
        self.dockbarThree.serverStatus.updateStatus("Connected to server: " + server)
        self.SETTINGS.setValue("Project/Server", server)
        self.MESSAGEHANDLER.info("Communications successfully initialized with the server.", popUp=True)

    def connectToServer(self, password: str, server: str, port: int = 3777) -> None:
        self.setStatus("Connecting to server...")
        if self.FCOM.isConnected():
            self.disconnectFromServer()

        self.MESSAGEHANDLER.info("Connecting to server: " + server)
        try:
            if self.FCOM.beginCommunications(password=password, server=server, port=port):
                status = "Getting Resolutions..."
                self.MESSAGEHANDLER.info(status)
                self.setStatus(status)
                self.FCOM.askServerForResolutions()
                status = "Getting Collectors..."
                self.MESSAGEHANDLER.info(status)
                self.setStatus(status)
                self.FCOM.askServerForCollectors(self.getClientCollectors())
                status = "Getting server projects list..."
                self.MESSAGEHANDLER.info(status)
                self.setStatus(status)
                self.FCOM.askProjectsList()
            else:
                self.setStatus('Failed to connect to server.')
        except ConnectionRefusedError:
            self.MESSAGEHANDLER.info("Connection Refused.", popUp=True)
        except Exception as exception:
            self.MESSAGEHANDLER.error(
                "Exception occurred while connecting to server: " + repr(exception))
            self.disconnectFromServer()
            return

    def disconnectFromServer(self) -> None:
        self.setStatus("Disconnecting from server...")
        if self.FCOM.isConnected():
            self.MESSAGEHANDLER.info("Closing existing connection...")
            self.FCOM.close()
            self.RESOLUTIONMANAGER.removeServerResolutions()
            self.dockbarOne.resolutionsPalette.loadAllResolutions()
            self.closeServerProjectListener()
            with self.serverProjectsLock:
                self.serverProjects = []
            with self.serverCollectorsLock:
                self.collectors = {}
                self.runningCollectors = {}
        self.setStatus("Disconnected from server.")
        self.dockbarThree.serverStatus.updateStatus("Not connected to a server")

    def addResolutionsFromServerListener(self, resolutions) -> None:
        self.setStatus("Adding Resolutions from Server...")
        self.RESOLUTIONMANAGER.loadResolutionsFromServer(resolutions)
        self.dockbarOne.resolutionsPalette.loadAllResolutions()

    def executeRemoteResolution(self, resolution_name: str, resolution_entities: list, resolution_parameters: dict,
                                resolution_uid: str):
        self.FCOM.runRemoteResolution(resolution_name, resolution_entities, resolution_parameters, resolution_uid)

    def cleanServerResolutionListener(self, resolution_uid: str) -> None:
        for resolutionThread in list(self.resolutions):
            if resolutionThread[0].uid == resolution_uid and resolutionThread[1] is True:
                if resolutionThread[0].isFinished():
                    self.resolutions.remove(resolutionThread)
                break

    def addCollectorsFromServerListener(self, server_collectors: dict, continuing_collectors_info: dict) -> None:
        with self.serverCollectorsLock:
            self.collectors = server_collectors
            self.runningCollectors = continuing_collectors_info

    def startNewCollectorListener(self, collector_category: str, collector_name: str, collector_uid: str,
                                  collector_entities: list, collector_parameters: dict):
        with self.serverCollectorsLock:
            if collector_category not in self.runningCollectors:
                self.runningCollectors[collector_category] = {}
            if collector_name not in self.runningCollectors[collector_category]:
                self.runningCollectors[collector_category][collector_name] = []

            # Re-running a collector would generate duplicate info; we don't want that.
            duplicateExists = False
            for collectorInstance in self.runningCollectors[collector_category][collector_name]:
                if collectorInstance['uid'] == collector_uid:
                    duplicateExists = True
                    break
            if not duplicateExists:
                self.runningCollectors[collector_category][collector_name].append({'uid': collector_uid,
                                                                                   'entities': collector_entities,
                                                                                   'parameters': collector_parameters})
        currentCollectors = self.getClientCollectors()
        currentCollectors[collector_uid] = time.time_ns() // 1000
        self.setClientCollectors(currentCollectors)

    def receiveProjectsListListener(self, projects: list) -> None:
        with self.serverProjectsLock:
            self.serverProjects = projects

    def receiveProjectCanvasesListListener(self, canvases: list) -> None:
        with self.syncedCanvasesLock:
            self.syncedCanvases = canvases

    def receiveProjectDeleteListener(self, deleted_project: str) -> None:
        with self.serverProjectsLock:
            try:
                self.serverProjects.remove(deleted_project)
                self.closeServerProjectListener()
            except ValueError:
                # If the client doesn't know about the deleted project, nothing to do.
                pass

    def openServerProjectListener(self, project_name: str) -> None:
        self.SETTINGS.setValue("Project/Server/Project", project_name)
        self.setStatus("Opened Server Project: " + project_name)
        self.dockbarThree.serverStatus.updateStatus("Connected to server: " +
                                                    self.SETTINGS.value("Project/Server") + " Project: " + project_name)
        self.syncDatabase()
        self.FCOM.askProjectCanvasesList(project_name)
        self.FCOM.askServerForFileList(project_name)
        self.MESSAGEHANDLER.info("Opened Server Project: " + project_name, popUp=True)

    def closeCurrentServerProject(self) -> None:
        if self.FCOM.isConnected():
            current_project = self.SETTINGS.value("Project/Server/Project")
            if current_project != "":
                self.FCOM.closeProject(current_project)
            else:
                self.MESSAGEHANDLER.warning('No Server Project to close.', popUp=True)
        else:
            self.MESSAGEHANDLER.warning('Not connected to a Server.', popUp=True)

    def closeServerProjectListener(self) -> None:
        project_name = self.SETTINGS.value("Project/Server/Project")
        server = self.SETTINGS.value("Project/Server")
        self.SETTINGS.setValue("Project/Server/Project", "")
        self.FCOM.receiveFileAbortAll(project_name)
        self.FCOM.sendFileAbortAll(project_name)
        self.unSyncCanvasByName()
        if server is not None:
            self.dockbarThree.serverStatus.updateStatus("Connected to server: " + server)
            if project_name != "":
                statusMessage = "Closed Server project: " + str(project_name)
                self.MESSAGEHANDLER.info(statusMessage)
                self.setStatus(statusMessage)

        self.dockbarOne.documentsList.updateFileListFromServer(None)
        with self.syncedCanvasesLock:
            self.syncedCanvases = []

    def openServerCanvasListener(self, canvas_name: str) -> None:
        project_name = self.SETTINGS.value("Project/Server/Project")
        self.setStatus("Opened Server Canvas: " + canvas_name + " on project: " + project_name)
        self.dockbarThree.serverStatus.updateStatus("Connected to server: " +
                                                    self.SETTINGS.value("Project/Server") + " Project: " +
                                                    project_name + " Canvas: " + canvas_name)

    def closeServerCanvasListener(self, canvas_name: str) -> None:
        project_name = self.SETTINGS.value("Project/Server/Project")
        self.centralWidget().tabbedPane.unmarkSyncedCanvasesByName(canvas_name)
        self.setStatus("Closed Server Canvas: " + canvas_name + " on project: " + project_name)
        self.dockbarThree.serverStatus.updateStatus("Connected to server: " +
                                                    self.SETTINGS.value("Project/Server") + " Project: " +
                                                    project_name)

    def syncDatabase(self):
        if self.FCOM.isConnected():
            project_name = self.SETTINGS.value("Project/Server/Project")
            if project_name != "":
                with self.LENTDB.dbLock:
                    self.FCOM.syncDatabase(project_name, self.LENTDB.database)
                self.MESSAGEHANDLER.info('Database Synced for project: ' + project_name)

    def syncCanvasByName(self, canvasName: str = None) -> None:
        """
        If canvasName is None, syncs the current canvas.
        :param canvasName:
        :return:
        """
        if self.FCOM.isConnected():
            project_name = self.SETTINGS.value("Project/Server/Project")
            if project_name != '':
                canvas_name, canvas_graph = self.centralWidget().tabbedPane.markCanvasAsSyncedByName(canvasName)
                if canvas_name is not None:
                    self.FCOM.syncCanvasSend(project_name, canvas_name, canvas_graph)
                    self.MESSAGEHANDLER.info('Syncing Canvas: ' + canvas_name)
                else:
                    self.setStatus('No canvas to sync!')
            else:
                self.setStatus('Must Create or Open a project on the Server before syncing canvases.')
        else:
            self.setStatus("Not connected to server.")

    def unSyncCurrentCanvas(self) -> None:
        currentCanvasName = self.centralWidget().tabbedPane.getCurrentView().name
        self.unSyncCanvasByName(currentCanvasName)

    def unSyncCanvasByName(self, canvasName: str = None) -> None:
        """
        If canvasName is None, unsyncs ALL canvases.
        Use 'unSyncCurrentCanvas' to unsync the current canvas.
        :param canvasName:
        :return:
        """
        self.centralWidget().tabbedPane.unmarkSyncedCanvasesByName(canvasName)
        project_name = self.SETTINGS.value("Project/Server/Project")
        if project_name != '':
            self.FCOM.closeCanvas(project_name, canvasName)
        if canvasName is not None:
            statusMessage = 'Stopped syncing Canvas: ' + canvasName
            self.setStatus(statusMessage)
            self.MESSAGEHANDLER.info(statusMessage)
        else:
            statusMessage = 'Stopped syncing all Canvases.'
            self.setStatus(statusMessage)
            self.MESSAGEHANDLER.info(statusMessage)

    def receiveSyncCanvasListener(self, canvas_name: str, canvas_nodes: dict, canvas_edges: dict) -> None:
        if canvas_name in self.centralWidget().tabbedPane.canvasTabs:
            canvasToSync = self.centralWidget().tabbedPane.canvasTabs[canvas_name]
            if canvasToSync.synced:
                canvasToSync.scene().syncCanvas(canvas_nodes, canvas_edges)
                self.MESSAGEHANDLER.debug('Canvas ' + canvas_name + ' synced.')

    def receiveSyncDatabaseListener(self, database_nodes: dict, database_edges: dict) -> None:
        """
        Handles received Database Sync events sent from the server.
        """
        self.LENTDB.mergeDatabases(database_nodes, database_edges, fromServer=True)
        self.MESSAGEHANDLER.debug('Project database synced.')

    def sendLocalCanvasUpdateToServer(self, canvas_name: str, entity_or_link_uid: Union[str, tuple]) -> None:
        if not self.FCOM.isConnected():
            return

        project_name = self.SETTINGS.value("Project/Server/Project")
        if project_name != '':
            self.FCOM.sendCanvasUpdateEvent(project_name, canvas_name, entity_or_link_uid)
            self.MESSAGEHANDLER.debug('Project canvas ' + canvas_name + ' send update for entity / link: ' +
                                      str(entity_or_link_uid))

    def receiveServerCanvasUpdate(self, canvas_name: str, entity_or_link_uid: Union[str, tuple]) -> None:
        scene = self.centralWidget().tabbedPane.getSceneByName(canvas_name)
        if scene is not None:
            # Check that the argument in the update is not empty.
            if entity_or_link_uid:
                if isinstance(entity_or_link_uid, str):
                    # Add Entity
                    if entity_or_link_uid not in scene.nodesDict:
                        scene.addNodeProgrammatic(entity_or_link_uid, fromServer=True)
                        scene.rearrangeGraph()
                else:
                    # Add Link
                    if entity_or_link_uid not in scene.linksDict:
                        scene.addLinkProgrammatic(entity_or_link_uid, fromServer=True)
                        scene.rearrangeGraph()

        self.MESSAGEHANDLER.debug('Received update to canvas: ' + canvas_name + ' for entity / link: ' +
                                  str(entity_or_link_uid))

    def sendLocalDatabaseUpdateToServer(self, entityJson: dict, add: int) -> None:
        """
        Called by the database when a local item event occurs.
        If connected to a server, the event is propagated to all other connected clients.
        """
        if not self.FCOM.isConnected():
            return
        project_name = self.SETTINGS.value("Project/Server/Project")
        if project_name != '':
            self.FCOM.sendDatabaseUpdateEvent(project_name, entityJson, add)
            self.MESSAGEHANDLER.debug('Sent database update to server: ' + str(entityJson) + ' - Operation: ' +
                                      str(add))

    def receiveServerDatabaseUpdate(self, entityJson: dict, add: int) -> None:
        # Check that the JSON received is not empty.
        if entityJson:
            uid = entityJson['uid']
            if add == 1:
                # Add item
                if isinstance(uid, str):
                    # Add Entity
                    self.LENTDB.addEntity(entityJson, fromServer=True)
                else:
                    # Add Link
                    self.centralWidget().tabbedPane.serverLinkAddHelper(entityJson)
            elif add == 2:
                # Remove item
                if isinstance(uid, str):
                    # Remove Entity
                    self.centralWidget().tabbedPane.nodeRemoveAllHelper(uid)
                    self.LENTDB.removeEntity(uid, fromServer=True)
                else:
                    # Remove Link
                    self.centralWidget().tabbedPane.linkRemoveAllHelper(uid)
                    self.LENTDB.removeLink(uid, fromServer=True)
            elif add == 3:
                # Overwrite existing link
                self.centralWidget().tabbedPane.serverLinkAddHelper(entityJson, overwrite=True)

        self.MESSAGEHANDLER.debug('Received database update from server: ' + str(entityJson) + ' - Operation: ' +
                                  str(add))

    def uploadFiles(self, items=None) -> None:
        if not self.FCOM.isConnected():
            self.setStatus("Not Connected to Server.")
            return

        project_name = self.SETTINGS.value("Project/Server/Project")
        if project_name == "":
            self.setStatus("No Open Project, cannot upload files.")
            self.MESSAGEHANDLER.warning("Must create or open a Server Project before uploading files.", popUp=True)
            return

        self.setStatus('Uploading...')

        itemsToUpload = []
        if items is not None:
            itemsToUpload = items
        else:
            materialsEntities = self.RESOURCEHANDLER.getAllEntitiesInCategory('Materials')
            projectFilesPath = Path(self.SETTINGS.value("Project/FilesDir"))
            for item in self.centralWidget().tabbedPane.getCurrentScene().selectedItems():
                itemJson = self.LENTDB.getEntity(item.uid)
                itemPath = projectFilesPath / itemJson['File Path']
                if itemJson.get('Entity Type') in materialsEntities and itemPath.exists() and itemPath.is_file():
                    itemsToUpload.append(itemJson)

        if not itemsToUpload:
            self.setStatus('No Materials Entities selected to upload to Server.')
            self.MESSAGEHANDLER.info('To send files to the server, please select any number of Entities on the '
                                     'current canvas. The type of each selected entity has to be one of the types '
                                     'in the "Materials" category.', popUp=True)
            return

        for item in itemsToUpload:
            fileDir = Path(self.SETTINGS.value("Project/FilesDir")) / item['File Path']
            file_name = item[self.RESOURCEHANDLER.getPrimaryFieldForEntityType(item['Entity Type'])]
            if file_name in [uploadingFileName.getFileName()
                             for uploadingFileName in self.dockbarOne.documentsList.uploadingFileWidgets]:
                continue
            if file_name in [uploadedFileName.getFileName()
                             for uploadedFileName in self.dockbarOne.documentsList.uploadedFileWidgets]:
                continue

            self.dockbarOne.documentsList.addUploadingFileToList(file_name)
            self.FCOM.sendFile(project_name, file_name, fileDir)

    def receiveAbortUploadOfFiles(self, file_name: Union[str, None]):
        """
        Remove file_name from documents widget on dockbar one.
        If None is passed instead of a string, all currently uploading files are removed.

        :param file_name:
        :return:
        """
        if file_name is not None:
            self.dockbarOne.documentsList.finishUploadingFile(file_name)
        else:
            for uploadingFile in list(self.dockbarOne.documentsList.uploadingFileWidgets):
                self.dockbarOne.documentsList.takeTopLevelItem(
                    self.dockbarOne.documentsList.indexOfTopLevelItem(uploadingFile))
                self.dockbarOne.documentsList.uploadingFileWidgets.remove(uploadingFile)

    def receiveFileListListener(self, fileList: list) -> None:
        self.MESSAGEHANDLER.debug('Received file list from server: ' + str(fileList))
        self.dockbarOne.documentsList.updateFileListFromServer(fileList)

    def fileUploadFinishedListener(self, file_name: str) -> None:
        self.MESSAGEHANDLER.debug('File upload finished:' + file_name)
        self.dockbarOne.documentsList.finishUploadingFile(file_name)

    def abortUpload(self, file_name: str) -> None:
        if self.FCOM.isConnected():
            project_name = self.SETTINGS.value("Project/Server/Project")
            if project_name != '':
                self.FCOM.sendFileAbort(project_name, file_name)

    def downloadFiles(self, items=None) -> None:
        if not self.FCOM.isConnected():
            self.setStatus("Not Connected to Server.")
            return

        project_name = self.SETTINGS.value("Project/Server/Project")
        if project_name == "":
            self.setStatus("No open Server Project, cannot download files.")
            self.MESSAGEHANDLER.warning("Must create or open a Server Project before downloading files.", popUp=True)
            return

        self.setStatus('Downloading...')

        itemsToDownload = []
        if items is not None:
            itemsToDownload = items
        else:
            materialsEntities = self.RESOURCEHANDLER.getAllEntitiesInCategory('Materials')
            projectFilesPath = Path(self.SETTINGS.value("Project/FilesDir"))
            for item in self.centralWidget().tabbedPane.getCurrentScene().selectedItems():
                itemJson = self.LENTDB.getEntity(item.uid)
                itemPath = projectFilesPath / itemJson['File Path']
                # Do not download files that already exist.
                if itemJson.get('Entity Type') in materialsEntities and not itemPath.exists():
                    itemsToDownload.append(itemJson)

        if not itemsToDownload:
            self.setStatus('No Materials Entities selected to download from Server.')
            self.MESSAGEHANDLER.info('To download files from the server, please select any number of Entities on the '
                                     'current canvas. The type of each selected entity has to be one of the types '
                                     'in the "Materials" category.', popUp=True)
            return

        for item in itemsToDownload:
            fileDir = Path(self.SETTINGS.value("Project/FilesDir")) / item['File Path']
            file_name = item[self.RESOURCEHANDLER.getPrimaryFieldForEntityType(item['Entity Type'])]
            self.FCOM.receiveFile(project_name, file_name, fileDir)

    def abortDownload(self, file_name: str) -> None:
        if self.FCOM.isConnected():
            project_name = self.SETTINGS.value("Project/Server/Project")
            if project_name != '':
                self.FCOM.receiveFileAbort(project_name, file_name)

    def getSummaryOfDocument(self, document_name: Union[str, None]) -> None:
        if self.FCOM.isConnected():
            project_name = self.SETTINGS.value("Project/Server/Project")
            if project_name != '':
                if document_name is None:
                    selectedDocuments = self.dockbarOne.documentsList.selectedItems()
                    if len(selectedDocuments) > 0:
                        document_name = selectedDocuments[0].getFileName()
                    else:
                        self.setStatus("Must upload and select document before obtaining summary.")
                        self.MESSAGEHANDLER.warning("Must upload and select document from 'Files Loaded' section "
                                                    "before getting summary.", popUp=True)
                self.FCOM.askServerForFileSummary(project_name, document_name)
            else:
                self.setStatus("Not Connected to Server.")
                self.MESSAGEHANDLER.info('Cannot get summary of documents: Not working on a Server Project.',
                                         popUp=True)
        else:
            self.setStatus("No currently open Server Project.")

            self.MESSAGEHANDLER.info('Cannot get summary of documents: Not connected to a Server.', popUp=True)

    def receiveSummaryOfDocument(self, document_name: str, summary: str):
        self.centralWidget().setDocTitleAndContents(document_name, summary)

    def askQuestion(self) -> None:
        question = self.dockbarTwo.oracle.questionSection.text()
        if not self.FCOM.isConnected():
            self.setStatus("Not Connected to Server.")
            self.dockbarTwo.oracle.answerSection.setPlainText(
                "Not connected to Server - Question Answering is disabled."
            )
        else:
            project_name = self.SETTINGS.value("Project/Server/Project")
            if project_name == "":
                self.setStatus("No Open Project, Question Answering system cannot be used.")
                self.dockbarTwo.oracle.answerSection.setPlainText(
                    "No open server Project - Question Answering is disabled."
                )
            else:
                self.dockbarTwo.oracle.answerSection.setPlainText("Calculating Answer...")
                self.MESSAGEHANDLER.info('Asking question: ' + question)
                self.FCOM.askQuestion(project_name, question,
                                      int(self.SETTINGS.value("Project/Question Answering Reader Value")),
                                      int(self.SETTINGS.value("Project/Question Answering Retriever Value")),
                                      int(self.SETTINGS.value("Project/Number of Answers Returned")))
                self.setStatus("Asked Question")

    def questionAnswerListener(self, response: list) -> None:
        textAns = "No Answer."
        answerCount = len(response)
        if answerCount != 0:
            textAns = ""
            for answerIndex in range(answerCount):
                answer = response[answerIndex]
                if answer['answer']:
                    textAns += "Answer " + str(answerIndex + 1) + ": " + answer['answer'] + "\n\n"
                    textAns += "Context: ..." + answer['context'] + "...\n\n"
                    textAns += "Document Used: " + answer['doc']
                    textAns += "\n\n"
                else:
                    textAns += "Answer " + str(answerIndex + 1) + ": No Answer\n\n"

        self.dockbarTwo.oracle.answerSection.setPlainText(textAns)
        self.setStatus("Answered Question")

    def sendChatMessage(self, chat_message: str) -> None:
        if not self.FCOM.isConnected():
            self.setStatus("Not Connected to Server.")
        else:
            project_name = self.SETTINGS.value("Project/Server/Project")
            if project_name == "":
                self.setStatus("No open Project.")
            else:
                self.FCOM.sendTextMessage(project_name, chat_message)

    def receiveChatMessage(self, message: str) -> None:
        self.dockbarThree.chatBox.receiveMessage(message)

    def initializeLayout(self) -> None:

        self.restoreGeometry(QtCore.QByteArray(self.SETTINGS.value("MainWindow/Geometry")))
        self.restoreState(QtCore.QByteArray(self.SETTINGS.value("MainWindow/WindowState")))

        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea,
                           self.dockbarOne)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea,
                           self.dockbarTwo)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea,
                           self.dockbarThree)

        self.addToolBar(self.primaryToolbar)
        self.setMenuBar(MenuBar.MenuBar(self))

        # Set the main window title and show it to the user.
        self.setWindowTitle("LinkScope - " + self.SETTINGS.get('Project/Name', 'Untitled'))
        iconPath = Path(self.SETTINGS.get('Program/BaseDir')) / 'Icon.ico'
        appIcon = QtGui.QIcon(str(iconPath))
        self.setWindowIcon(appIcon)
        self.trayIcon = QtWidgets.QSystemTrayIcon(appIcon, self)
        # Whether the icon is shown or not depends on the Desktop environment.
        self.trayIcon.show()

        self.dockbarOne.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)
        self.dockbarTwo.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)
        self.dockbarThree.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)

        # Autosave approximately once every ten minutes.
        # Margin of error: 500 ms.
        self.saveTimer.start(600000)

        self.show()

        # Moved this here so the software doesn't crash if there are a ton of nodes.
        self.centralWidget().tabbedPane.open()
        # Creating default 'Home' tab, if no tabs exist.
        if len(self.centralWidget().tabbedPane.canvasTabs) == 0:
            self.centralWidget().tabbedPane.createHomeTab()

        self.setStatus("Ready")
        self.MESSAGEHANDLER.info('Project opened, ready to work.')

    def __init__(self):
        super(MainWindow, self).__init__()
        self.linkingNodes = False
        self.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)

        # Create or open project
        nW = NewOrOpenWidget(self)
        nW.exec()

        if not nW.createProject and nW.openProject is None:
            sys.exit()

        self.SETTINGS = SettingsObject.SettingsObject()
        if nW.createProject:
            self.SETTINGS.setValue(
                "Project/BaseDir", str(Path(nW.pDir.text()).joinpath(nW.pName.text())))
            self.SETTINGS.setValue("Project/FilesDir",
                                   str(Path(self.SETTINGS.value("Project/BaseDir")).joinpath("Project Files")))
            self.SETTINGS.setValue("Project/Name", nW.pName.text())
            self.SETTINGS.setValue("Program/BaseDir", dirname(abspath(getsourcefile(lambda: 0))))

            try:
                Path(self.SETTINGS.value("Project/BaseDir")
                     ).mkdir(0o700, parents=False, exist_ok=False)
                Path(self.SETTINGS.value("Project/FilesDir")
                     ).mkdir(0o700, parents=False, exist_ok=False)
            except FileExistsError:
                QtWidgets.QMessageBox.warning(self, 'Cannot create project',
                                              'Cannot save project to an existing directory. '
                                              'Please choose a unique name.',
                                              QtWidgets.QMessageBox.Ok)
                return
            except FileNotFoundError:
                QtWidgets.QMessageBox.warning(self, 'Cannot create project',
                                              'Cannot save project into a non-existing parent directory.'
                                              'Please create the required parent directories and try again.',
                                              QtWidgets.QMessageBox.Ok)
                return

        elif nW.openProject is not None:
            projectDir = Path(nW.openProject).parent.absolute()
            projectDirFile = open(nW.openProject, "rb")
            self.SETTINGS.load(load(projectDirFile))
            projectDirFile.close()

            # Re-set file path related settings in case the project or the software was moved.
            self.SETTINGS.setValue("Program/BaseDir", dirname(abspath(getsourcefile(lambda: 0))))
            self.SETTINGS.setValue("Project/BaseDir", str(projectDir))
            self.SETTINGS.setValue("Project/FilesDir", str(projectDir / "Project Files"))

        self.MESSAGEHANDLER = MessageHandler.MessageHandler(self)
        self.RESOURCEHANDLER = ResourceHandler.ResourceHandler(self, self.MESSAGEHANDLER)
        self.dockbarThree = DockBarThree.DockBarThree(self)
        self.LENTDB = EntityDB.EntitiesDB(self, self.MESSAGEHANDLER, self.RESOURCEHANDLER)
        self.URLMANAGER = URLManager.URLManager(self)
        self.RESOLUTIONMANAGER = ResolutionManager.ResolutionManager(self, self.MESSAGEHANDLER)
        self.FCOM = FrontendCommunicationsHandler.CommunicationsHandler(self)

        # Have the project auto-save on regular intervals by default.
        self.saveTimer = QtCore.QTimer(self)
        self.saveTimer.timeout.connect(self.autoSaveProject)
        self.saveTimer.setSingleShot(False)
        self.saveTimer.setTimerType(QtCore.Qt.VeryCoarseTimer)

        self.syncedCanvases = []
        self.syncedCanvasesLock = threading.Lock()
        self.serverProjects = []
        self.serverProjectsLock = threading.Lock()
        self.resolutions = []
        self.serverCollectorsLock = threading.Lock()
        self.collectors = {}
        self.runningCollectors = {}

        self.RESOLUTIONMANAGER.loadResolutionsFromDir(
            Path(self.SETTINGS.value("Program/BaseDir")) / "Core" / "Resolutions" / "Core")

        self.entityTextFont = QtGui.QFont(self.SETTINGS.value("Program/EntityTextFontType"),
                                          int(self.SETTINGS.value("Program/EntityTextFontSize")),
                                          int(self.SETTINGS.value("Program/EntityTextFontBoldness")))
        self.entityTextBrush = QtGui.QBrush(self.SETTINGS.value("Program/EntityTextColor"))
        self.linkTextFont = QtGui.QFont(self.SETTINGS.value("Program/LinkTextFontType"),
                                        int(self.SETTINGS.value("Program/LinkTextFontSize")),
                                        int(self.SETTINGS.value("Program/LinkTextFontBoldness")))
        self.linkTextBrush = QtGui.QBrush(self.SETTINGS.value("Program/LinkTextColor"))

        self.setCentralWidget(CentralPane.WorkspaceWidget(self,
                                                          self.MESSAGEHANDLER,
                                                          self.URLMANAGER,
                                                          self.LENTDB,
                                                          self.RESOURCEHANDLER,
                                                          self.entityTextFont,
                                                          self.entityTextBrush,
                                                          self.linkTextFont,
                                                          self.linkTextBrush))

        self.facilitateResolutionSignalListener.connect(self.centralWidget().tabbedPane.facilitateResolution)

        self.loadModules()

        # Sort the resolutions alphabetically.
        self.RESOLUTIONMANAGER.resolutions = dict(sorted(self.RESOLUTIONMANAGER.resolutions.items()))

        self.dockbarOne = DockBarOne.DockBarOne(
            self,
            self.RESOLUTIONMANAGER,
            self.RESOURCEHANDLER,
            self.LENTDB)

        self.dockbarTwo = DockBarTwo.DockBarTwo(self,
                                                self.RESOURCEHANDLER,
                                                self.LENTDB)

        self.primaryToolbar = ToolBarOne.ToolBarOne('Primary Toolbar', self)

        self.trayIcon = None
        # Cannot specify icon if notification spawned from signal.
        self.notifyUserSignalListener.connect(self.notifyUser)

        self.initializeLayout()


class ReportWizard(QtWidgets.QWizard):
    def __init__(self, parent):
        super(ReportWizard, self).__init__(parent=parent)

        self.primaryFieldsList = []

        self.addPage(InitialConfigPage(self))
        self.addPage(TitlePage(self))

        self.addPage(SummaryPage(self))

        self.selectedNodes = [entity for entity in
                              self.parent().centralWidget().tabbedPane.getCurrentScene().selectedItems()
                              if isinstance(entity, BaseNode)]
        for selectedNode in self.selectedNodes:
            # used in wizard
            self.primaryField = selectedNode.labelItem.text()
            self.uid = selectedNode.uid

            # used in report generation
            self.primaryFieldsList.append(self.primaryField)
            self.addPage(EntityPage(self))

        self.setWizardStyle(QtWidgets.QWizard.ModernStyle)
        self.setWindowTitle("Generate Report Wizard")

        self.button(QtWidgets.QWizard.FinishButton).clicked.connect(self.onFinish)

    def onFinish(self):
        reportData = []

        outgoingEntitiesForEachEntity = []
        incomingEntitiesForEachEntity = []
        outgoingEntityPrimaryFieldsForEachEntity = []
        incomingEntityPrimaryFieldsForEachEntity = []

        entityList = []
        for pageID in self.pageIds():
            pageObject = self.page(pageID)
            reportData.append(pageObject.getData())

        for selectedNode in self.selectedNodes:
            uid = selectedNode.uid
            entityList.append(self.parent().LENTDB.getEntity(uid))
            outgoing = self.parent().LENTDB.getOutgoingLinks(uid)
            incoming = self.parent().LENTDB.getIncomingLinks(uid)

            outgoingEntities = []
            incomingEntities = []
            outgoingNames = []
            incomingNames = []

            for out in outgoing:
                outLink = self.parent().LENTDB.getLink(out)
                outgoingEntities.append(outLink)
                outgoingEntityJson = self.parent().LENTDB.getEntity(outLink['uid'][1])
                outgoingNames.append(outgoingEntityJson[list(outgoingEntityJson)[1]])

            for inc in incoming:
                inLink = self.parent().LENTDB.getLink(inc)
                incomingEntities.append(inLink)
                incomingEntityJson = self.parent().LENTDB.getEntity(inLink['uid'][0])

                incomingNames.append(incomingEntityJson[list(incomingEntityJson)[1]])

            outgoingEntityPrimaryFieldsForEachEntity.append(outgoingNames)
            incomingEntityPrimaryFieldsForEachEntity.append(incomingNames)
            outgoingEntitiesForEachEntity.append(outgoingEntities)
            incomingEntitiesForEachEntity.append(incomingEntities)

        path = Path(reportData[0].get('SavePath'))

        canvas = reportData[2].get('CanvasName')
        viewPortBool = reportData[2].get('ViewPort')

        canvasPicture = self.parent().getPictureOfCanvas(canvas, viewPortBool, True)
        temp_dir = tempfile.TemporaryDirectory()
        canvasImagePath = Path(temp_dir.name) / 'canvas.png'
        canvasPicture.save(str(canvasImagePath), "PNG")

        # timelinePicture = self.parent().dockbarThree.timeWidget.takePictureOfView(False)
        # timelineImagePath = Path(temp_dir.name) / 'timeline.png'
        # timelinePicture.save(str(timelineImagePath), "PNG")

        savePath = Path(reportData[0]['SavePath']).absolute()

        try:
            ReportGeneration.PDFReport(str(path), reportData, outgoingEntitiesForEachEntity,
                                       incomingEntitiesForEachEntity, entityList, canvasImagePath, None,  # <timelinePic
                                       self.primaryFieldsList, incomingEntityPrimaryFieldsForEachEntity,
                                       outgoingEntityPrimaryFieldsForEachEntity)

            self.parent().MESSAGEHANDLER.debug(reportData)
            self.parent().MESSAGEHANDLER.info("Saved Report at: " + str(savePath), popUp=True)
        except PermissionError:
            self.parent().MESSAGEHANDLER.error("Could not generate report. No permission to save at the chosen "
                                               "location: " + str(savePath), popUp=True, exc_info=False)
        except Exception as exc:
            self.parent().MESSAGEHANDLER.error("Could not generate report: " + str(exc), popUp=True, exc_info=True)
        finally:
            # Technically not necessary as the temp directory is deleted.
            canvasImagePath.unlink(missing_ok=True)


class InitialConfigPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super(InitialConfigPage, self).__init__(parent)
        self.subtitleLabel = QtWidgets.QLabel("Path to save the report at: ")
        self.savePathEdit = QtWidgets.QLineEdit()
        self.setTitle(self.tr("Initial Configuration Wizard"))

        pDirButton = QtWidgets.QPushButton("Save Report As...")
        pDirButton.clicked.connect(self.editPath)

        hLayout = QtWidgets.QVBoxLayout()
        hLayout.addWidget(self.subtitleLabel)
        hLayout.addWidget(self.savePathEdit)
        hLayout.addWidget(pDirButton)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(hLayout)
        self.setLayout(layout)

    def editPath(self):
        selectedPath = QtWidgets.QFileDialog.getSaveFileName(self,
                                                             "File Name to Save As",
                                                             str(Path.home()),
                                                             filter="PDF Files (*.pdf)",
                                                             options=QtWidgets.QFileDialog.DontUseNativeDialog)
        selectedPath = selectedPath[0]
        if selectedPath != '':
            self.savePathEdit.setText(str(Path(selectedPath).absolute()))

    def getData(self):
        data = {'SavePath': self.savePathEdit.text()}
        return data


class TitlePage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super(TitlePage, self).__init__(parent)
        self.inputTitleEdit = QtWidgets.QLineEdit()
        self.inputSubtitleEdit = QtWidgets.QLineEdit()
        self.inputAuthorsEdit = QtWidgets.QLineEdit()
        self.setTitle(self.tr("Title Page Wizard"))

        titleLabel = QtWidgets.QLabel("Title: ")
        subtitleLabel = QtWidgets.QLabel("Subtitle: ")
        authorsLabel = QtWidgets.QLabel("Authors: ")

        hLayout = QtWidgets.QVBoxLayout()
        hLayout.addWidget(titleLabel)
        hLayout.addWidget(self.inputTitleEdit)
        hLayout.addWidget(subtitleLabel)
        hLayout.addWidget(self.inputSubtitleEdit)
        hLayout.addWidget(authorsLabel)
        hLayout.addWidget(self.inputAuthorsEdit)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(hLayout)
        self.setLayout(layout)

    def getData(self):
        data = {'Title': self.inputTitleEdit.text(), 'Subtitle': self.inputSubtitleEdit.text(),
                'Authors': self.inputAuthorsEdit.text()}
        return data


class SummaryPage(QtWidgets.QWizardPage):
    def __init__(self, parent):
        super(SummaryPage, self).__init__(parent=parent.parent())
        self.setTitle(self.tr("Summary Page Wizard"))
        self.inputNotesEdit = QtWidgets.QPlainTextEdit()
        self.canvasDropDownMenu = QtWidgets.QComboBox()
        self.viewPortCheckBox = QtWidgets.QCheckBox('ViewPort Only')
        self.viewPortCheckBox.setChecked(False)
        self.canvasNames = list(self.parent().centralWidget().tabbedPane.canvasTabs.keys())

        summaryLabel = QtWidgets.QLabel("Summary Notes: ")

        canvasLabel = QtWidgets.QLabel("Select canvas to be displayed: ")
        for canvas in self.canvasNames:
            self.canvasDropDownMenu.addItem(canvas)

        hLayout = QtWidgets.QVBoxLayout()
        hLayout.addWidget(summaryLabel)
        hLayout.addWidget(self.inputNotesEdit)
        hLayout.addWidget(canvasLabel)
        hLayout.addWidget(self.viewPortCheckBox)
        hLayout.addWidget(self.canvasDropDownMenu)
        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(hLayout)
        self.setLayout(layout)

    def getData(self):
        data = {'SummaryNotes': self.inputNotesEdit.toPlainText(), 'CanvasName': self.canvasDropDownMenu.currentText(),
                'ViewPort': self.viewPortCheckBox.isChecked()}
        return data


class EntityPage(QtWidgets.QWizardPage):
    def __init__(self, parent: ReportWizard):
        super(EntityPage, self).__init__(parent=parent.parent())
        self.inputAppendixImageEdit = QtWidgets.QLineEdit()
        self.appendixWidget = QtWidgets.QWidget()
        self.appendixLayout = QtWidgets.QVBoxLayout()

        self.setTitle(self.tr(f"Entity Page Wizard"))
        self.setMinimumSize(300, 700)

        self.entityName = parent.primaryField
        self.uidPicture = parent.uid

        self.inputNotesEdit = QtWidgets.QPlainTextEdit()
        self.inputImageEdit = QtWidgets.QLineEdit()
        self.button = QtWidgets.QPushButton("Add...")

        self.scrolllayout = QtWidgets.QVBoxLayout()
        self.scrollwidget = QtWidgets.QWidget()

        self.defaultpic = self.parent().LENTDB.getEntity(self.uidPicture).get('Icon')

        summaryLabel = QtWidgets.QLabel(f"Entity {self.entityName} Notes: ")

        imageLabel = QtWidgets.QLabel("Image Path: ")
        pDirButton = QtWidgets.QPushButton("Select Image...")
        pDirButton.clicked.connect(self.editPath)
        pDirButton.setDisabled(True)
        imageCheckBox = QtWidgets.QCheckBox('Add Custom Entity Image')
        imageCheckBox.setChecked(False)
        imageCheckBox.toggled.connect(pDirButton.setEnabled)

        self.button.clicked.connect(self.addSection)

        self.button.setDisabled(True)

        appendixCheckBox = QtWidgets.QCheckBox('Add Appendix')
        appendixCheckBox.setChecked(False)
        appendixCheckBox.toggled.connect(self.button.setEnabled)

        self.scrollwidget.setLayout(self.scrolllayout)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.scrollwidget)

        hLayout = QtWidgets.QVBoxLayout()
        hLayout.addWidget(summaryLabel)
        hLayout.addWidget(self.inputNotesEdit)

        hLayout.addWidget(imageCheckBox)
        hLayout.addWidget(imageLabel)
        hLayout.addWidget(self.inputImageEdit)
        hLayout.addWidget(pDirButton)

        hLayout.addWidget(appendixCheckBox)
        hLayout.addWidget(self.button)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(hLayout)
        layout.addWidget(scroll)

        self.setLayout(layout)

    def editPath(self):
        selectedPath = QtWidgets.QFileDialog().getOpenFileName(parent=self, caption='Select New Icon',
                                                               dir=str(Path.home()),
                                                               options=QtWidgets.QFileDialog.DontUseNativeDialog,
                                                               filter="Image Files (*.png *.jpg)")[0]
        if selectedPath != '':
            self.inputImageEdit.setText(str(Path(selectedPath).absolute()))

    def editAppendixPath(self):
        selectedPath = QtWidgets.QFileDialog().getOpenFileName(parent=self, caption='Select New Icon',
                                                               dir=str(Path.home()),
                                                               options=QtWidgets.QFileDialog.DontUseNativeDialog,
                                                               filter="Image Files (*.png *.jpg)")[0]
        if selectedPath != '':
            self.inputAppendixImageEdit.setText(str(Path(selectedPath).absolute()))

    def addSection(self):
        appendixLabelNotes = QtWidgets.QLabel("Entity Notes: ")
        inputAppendixNotesEdit = QtWidgets.QPlainTextEdit()
        imageAppendixLabel = QtWidgets.QLabel("Image Path: ")
        appendixButton = QtWidgets.QPushButton("Select Image...")
        appendixButton.clicked.connect(self.editAppendixPath)
        self.appendixLayout.addWidget(appendixLabelNotes)
        self.appendixLayout.addWidget(inputAppendixNotesEdit)
        self.appendixLayout.addWidget(imageAppendixLabel)
        self.appendixLayout.addWidget(self.inputAppendixImageEdit)
        self.appendixLayout.addWidget(appendixButton)
        self.appendixWidget.setLayout(self.appendixLayout)
        self.scrolllayout.addWidget(self.appendixWidget)
        self.button.setDisabled(True)

    def getData(self):
        import re
        from svglib.svglib import svg2rlg

        appendixNotes = []
        if self.inputImageEdit.text() != '':
            data = {'EntityNotes': self.inputNotesEdit.toPlainText(), 'EntityImage': self.inputImageEdit.text()}
        else:
            if 'svg' in str(self.defaultpic):
                contents = bytearray(self.defaultpic)
                widthRegex = re.compile(b' width="\d*" ')
                fileContents = ''
                for widthMatches in widthRegex.findall(self.defaultpic):
                    fileContents = contents.replace(widthMatches, b' ')
                heightRegex = re.compile(b' height="\d*" ')
                for heightMatches in heightRegex.findall(self.defaultpic):
                    fileContents = contents.replace(heightMatches, b' ')
                fileContents = fileContents.replace(b'<svg ', b'<svg height="150" width="150" ')

                temp_dir = tempfile.TemporaryDirectory()
                imagePath = Path(temp_dir.name) / 'entity.svg'
                with open(imagePath, 'wb') as tempFile:
                    tempFile.write(bytearray(fileContents))

                image = svg2rlg(imagePath)
                data = {'EntityNotes': self.inputNotesEdit.toPlainText(), 'EntityImage': image}
            elif 'PNG' in str(self.defaultpic):
                temp_dir = tempfile.TemporaryDirectory()
                imagePath = Path(temp_dir.name) / 'entity.png'
                with open(imagePath, 'wb') as tempFile:
                    tempFile.write(bytearray(self.defaultpic.data()))

                data = {'EntityNotes': self.inputNotesEdit.toPlainText(), 'EntityImage': str(imagePath)}
            else:
                self.defaultpic = self.parent().RESOURCEHANDLER.getEntityDefaultPicture(
                    self.parent().LENTDB.getEntity(self.uidPicture)['Entity Type'])
                # Default picture is an SVG.
                contents = bytearray(self.defaultpic)
                widthRegex = re.compile(b' width="\d*" ')
                fileContents = ''
                for widthMatches in widthRegex.findall(self.defaultpic):
                    fileContents = contents.replace(widthMatches, b' ')
                heightRegex = re.compile(b' height="\d*" ')
                for heightMatches in heightRegex.findall(self.defaultpic):
                    fileContents = contents.replace(heightMatches, b' ')
                fileContents = fileContents.replace(b'<svg ', b'<svg height="150" width="150" ')

                temp_dir = tempfile.TemporaryDirectory()
                imagePath = Path(temp_dir.name) / 'entity.svg'
                with open(imagePath, 'wb') as tempFile:
                    tempFile.write(bytearray(fileContents))

                image = svg2rlg(imagePath)
                data = {'EntityNotes': self.inputNotesEdit.toPlainText(), 'EntityImage': image}

        qPlainTextNote = self.appendixWidget.findChildren(QtWidgets.QPlainTextEdit)
        qlineEdits = self.appendixWidget.findChildren(QtWidgets.QLineEdit)
        for i in range(len(qPlainTextNote)):
            appendixDict = {'AppendixEntityNotes': qPlainTextNote[i].toPlainText(),
                            'AppendixEntityImage': qlineEdits[i].text()}
            appendixNotes.append(appendixDict)

        return data, appendixNotes


class CreateOrOpenCanvas(QtWidgets.QDialog):

    def __init__(self, parent, isConnectedToNetwork=False, syncedCanvases=None):
        super().__init__(parent=parent)
        if syncedCanvases is None:
            syncedCanvases = []
        dialogLayout = QtWidgets.QGridLayout()
        self.setLayout(dialogLayout)
        self.setWindowTitle("Create New Canvas Or Open Existing")
        self.setMinimumSize(400, 200)

        createCanvasTitleLabel = QtWidgets.QLabel("Create New Canvas")
        createCanvasTitleLabel.setStyleSheet(Stylesheets.DOCK_BAR_LABEL)

        createCanvasTitleLabel.setFont(QtGui.QFont("Times", 13, QtGui.QFont.Bold))

        createCanvasTitleLabel.setAlignment(QtCore.Qt.AlignCenter)
        createCanvasNameLabel = QtWidgets.QLabel("New Canvas Name:")
        self.createCanvasTextbox = QtWidgets.QLineEdit("")
        createCanvasButton = QtWidgets.QPushButton("Create New Canvas")
        createCanvasButton.clicked.connect(self.confirmCreateCanvas)

        dialogLayout.addWidget(createCanvasTitleLabel, 0, 0, 1, 4)
        dialogLayout.addWidget(createCanvasNameLabel, 1, 0, 1, 2)
        dialogLayout.addWidget(self.createCanvasTextbox, 1, 2, 1, 2)
        dialogLayout.addWidget(createCanvasButton, 2, 1, 1, 2)
        # Add some space in the layout
        spacer = QtWidgets.QLabel()
        spacer.setStyleSheet(Stylesheets.DOCK_BAR_TWO_LINK)
        dialogLayout.addWidget(spacer, 3, 1)

        openExistingCanvasTitleLabel = QtWidgets.QLabel("Open Existing Canvas")
        openExistingCanvasTitleLabel.setStyleSheet(Stylesheets.DOCK_BAR_LABEL)

        openExistingCanvasTitleLabel.setFont(QtGui.QFont("Times", 13, QtGui.QFont.Bold))

        openExistingCanvasTitleLabel.setAlignment(QtCore.Qt.AlignCenter)
        openExistingCanvasNameLabel = QtWidgets.QLabel("Canvas Name:")
        self.openExistingCanvasDropdown = QtWidgets.QComboBox()
        self.openExistingCanvasDropdown.setEditable(False)
        self.openExistingCanvasDropdown.SizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        tabbedPane = self.parent().centralWidget().tabbedPane
        canvasTabs = tabbedPane.canvasTabs
        existingTabNames = []
        for tabIndex in range(tabbedPane.count()):
            existingTabNames.append(tabbedPane.tabText(tabIndex))

        openExistingCanvasButton = QtWidgets.QPushButton('Open Existing Canvas')
        openExistingCanvasButton.clicked.connect(self.confirmOpenExistingCanvas)

        canvasesToOpen = [tabName for tabName in canvasTabs if tabName not in existingTabNames]
        self.openExistingCanvasDropdown.addItems(canvasesToOpen)

        if len(canvasesToOpen) == 0:
            self.openExistingCanvasDropdown.setEnabled(False)
            openExistingCanvasButton.setEnabled(False)

        dialogLayout.addWidget(openExistingCanvasTitleLabel, 4, 0, 1, 4)
        dialogLayout.addWidget(openExistingCanvasNameLabel, 5, 0, 1, 2)
        dialogLayout.addWidget(self.openExistingCanvasDropdown, 5, 2, 1, 2)
        dialogLayout.addWidget(openExistingCanvasButton, 6, 1, 1, 2)
        # Add some space in the layout
        spacer = QtWidgets.QLabel()
        spacer.setStyleSheet(Stylesheets.DOCK_BAR_TWO_LINK)
        dialogLayout.addWidget(spacer, 7, 1)

        openServerCanvasTitleLabel = QtWidgets.QLabel("Open Canvas From Server")
        openServerCanvasTitleLabel.setStyleSheet(Stylesheets.DOCK_BAR_LABEL)

        openServerCanvasTitleLabel.setFont(QtGui.QFont("Times", 13, QtGui.QFont.Bold))

        openServerCanvasTitleLabel.setAlignment(QtCore.Qt.AlignCenter)
        openServerCanvasNameLabel = QtWidgets.QLabel("Canvas Name:")
        self.openServerCanvasDropdown = QtWidgets.QComboBox()
        self.openServerCanvasDropdown.setEditable(False)
        self.openServerCanvasDropdown.SizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.openServerCanvasDropdown.addItems(syncedCanvases)
        openServerCanvasButton = QtWidgets.QPushButton("Open Canvas from Server")
        openServerCanvasButton.clicked.connect(self.confirmOpenServerCanvas)

        if not isConnectedToNetwork or syncedCanvases == []:
            self.openServerCanvasDropdown.setEnabled(False)
            openServerCanvasButton.setEnabled(False)

        dialogLayout.addWidget(openServerCanvasTitleLabel, 8, 0, 1, 4)
        dialogLayout.addWidget(openServerCanvasNameLabel, 9, 0, 1, 2)
        dialogLayout.addWidget(self.openServerCanvasDropdown, 9, 2, 1, 2)
        dialogLayout.addWidget(openServerCanvasButton, 10, 1, 1, 2)
        self.canvasName = ""

    def confirmCreateCanvas(self):
        self.canvasName = self.createCanvasTextbox.text()
        createStatus = self.parent().centralWidget().tabbedPane.addCanvas(self.canvasName)
        if createStatus:
            self.accept()
        else:
            self.parent().MESSAGEHANDLER.warning("A Canvas with that name already exists!", popUp=True)

    def confirmOpenServerCanvas(self):
        self.canvasName = self.openServerCanvasDropdown.currentText()
        createStatus = self.parent().centralWidget().tabbedPane.addCanvas(self.canvasName)
        if createStatus:
            self.parent().syncCanvasByName(self.canvasName)
            self.accept()
        else:
            self.parent().MESSAGEHANDLER.warning("A Canvas with that name already exists!", popUp=True)

    def confirmOpenExistingCanvas(self):
        self.canvasName = self.openExistingCanvasDropdown.currentText()
        self.parent().centralWidget().tabbedPane.showTab(self.canvasName)
        self.accept()


class NewOrOpenWidget(QtWidgets.QDialog):
    """
    If self.openProject is not None, then the user opened a project.
    If it is none, check self.pName (Project Name) and self.pDir
    (Project Directory).
    """

    def __init__(self, parent):
        super().__init__(parent=parent)

        newOrOpenLayout = QtWidgets.QGridLayout()
        self.setLayout(newOrOpenLayout)
        self.setWindowTitle("Create New Project Or Open Existing")
        self.setMinimumSize(700, 300)
        self.setObjectName("settingsWidget")
        self.setStyleSheet(Stylesheets.SETTINGS_WIDGET_STYLESHEET)

        # New Project
        self.createProject = False
        newProjectNameLabel = QtWidgets.QLabel("New Project")
        newProjectNameLabel.setStyleSheet(Stylesheets.MENUS_STYLESHEET)
        newProjectNameLabel.setAlignment(QtCore.Qt.AlignCenter)

        pProjectPathLabel = QtWidgets.QLabel("Project Path:")
        pProjectPathLabel.setStyleSheet(Stylesheets.MENUS_STYLESHEET)
        pDirLabel = QtWidgets.QLabel("Directory")
        pDirLabel.setStyleSheet(Stylesheets.MENUS_STYLESHEET)
        pDirLabel.setAlignment(QtCore.Qt.AlignCenter)
        pNameLabel = QtWidgets.QLabel("Name")
        pNameLabel.setStyleSheet(Stylesheets.MENUS_STYLESHEET)
        pNameLabel.setAlignment(QtCore.Qt.AlignCenter)
        pSlashLabel = QtWidgets.QLabel("/")
        pSlashLabel.setStyleSheet(Stylesheets.MENUS_STYLESHEET)
        pSlashLabel.setAlignment(QtCore.Qt.AlignCenter)

        self.pName = QtWidgets.QLineEdit("Untitled")
        self.pName.setStyleSheet(Stylesheets.PATH_INPUT_STYLESHEET)
        self.pDir = QtWidgets.QLineEdit("")
        self.pDir.setStyleSheet(Stylesheets.PATH_INPUT_STYLESHEET)
        self.pDir.setMinimumSize(400, 10)
        self.pDir.setReadOnly(True)

        pDirButton = QtWidgets.QPushButton("Select Directory...")
        pDirButton.setStyleSheet(Stylesheets.BUTTON_STYLESHEET)
        pDirButton.clicked.connect(self.selectProjectDirectory)
        newProjectConfirm = QtWidgets.QPushButton("Create")
        newProjectConfirm.setStyleSheet(Stylesheets.BUTTON_STYLESHEET)

        newProjectConfirm.clicked.connect(self.createNewProject)

        newOrOpenLayout.addWidget(newProjectNameLabel, 0, 0, 1, 4)
        newOrOpenLayout.addWidget(pDirLabel, 1, 1)
        newOrOpenLayout.addWidget(pNameLabel, 1, 3)
        newOrOpenLayout.addWidget(pProjectPathLabel, 2, 0)
        newOrOpenLayout.addWidget(pSlashLabel, 2, 2)

        newOrOpenLayout.addWidget(self.pDir, 2, 1)
        newOrOpenLayout.addWidget(self.pName, 2, 3)
        newOrOpenLayout.addWidget(pDirButton, 3, 1)
        newOrOpenLayout.addWidget(newProjectConfirm, 3, 3)

        # Existing
        self.openProject = None
        openProjectFileLabel = QtWidgets.QLabel("Open Project File")
        openProjectFileLabel.setStyleSheet(Stylesheets.MENUS_STYLESHEET)
        openProjectFileLabel.setAlignment(QtCore.Qt.AlignCenter)
        openProjectButton = QtWidgets.QPushButton("Open...")
        openProjectButton.setStyleSheet(Stylesheets.BUTTON_STYLESHEET)
        openProjectButton.clicked.connect(self.openFilename)
        newOrOpenLayout.addWidget(openProjectFileLabel, 5, 0, 1, 4)
        newOrOpenLayout.addWidget(openProjectButton, 6, 0, 1, 4)

    def createNewProject(self):
        errorMessage = ""
        newProjectDir = Path(self.pDir.text()) / self.pName.text()
        if not access(self.pDir.text(), R_OK | W_OK):
            errorMessage += "Chosen Directory is not Readable and Writeable!\n"
        if newProjectDir.exists():
            errorMessage += "Chosen Project Path already exists!\n"
        if errorMessage != "":
            showError = QtWidgets.QMessageBox(self)
            showError.setText(errorMessage)
            showError.setStandardButtons(QtWidgets.QMessageBox().Ok)
            showError.setDefaultButton(QtWidgets.QMessageBox().Ok)
            showError.exec()

        else:
            self.createProject = True
            self.close()

    def selectProjectDirectory(self):

        self.setStyleSheet(Stylesheets.SELECT_PROJECT_STYLESHEET)

        filename = QtWidgets.QFileDialog.getExistingDirectory(self,
                                                              "Select Project Directory",
                                                              str(Path.home()),
                                                              options=QtWidgets.QFileDialog.DontUseNativeDialog)
        if access(filename, R_OK | W_OK):
            self.pDir.setText(filename)

    def openFilename(self):

        self.setStyleSheet(Stylesheets.SELECT_PROJECT_STYLESHEET)

        filename = QtWidgets.QFileDialog.getOpenFileName(self,
                                                         "Open Project File",
                                                         str(Path.home()),
                                                         "LinkScope Projects(*.linkscope)",
                                                         options=QtWidgets.QFileDialog.DontUseNativeDialog)

        if filename[0].endswith('.linkscope') and access(filename[0], R_OK | W_OK):
            self.openProject = filename[0]
            self.close()


class ResolutionExecutorThread(QtCore.QThread):
    sig = QtCore.Signal(str, dict)
    sigError = QtCore.Signal(str)

    def __init__(self, resolution: str, resolutionArgument: list, resolutionParameters: dict,
                 mainWindowObject: MainWindow, uid: str):
        super().__init__()
        self.resolution = resolution
        self.resolutionArgument = resolutionArgument
        self.resolutionParameters = resolutionParameters
        self.mainWindow = mainWindowObject
        self.return_results = True
        self.uid = uid
        self.done = False

    def run(self) -> None:
        try:
            ret = self.mainWindow.RESOLUTIONMANAGER.executeResolution(self.resolution,
                                                                      self.resolutionArgument,
                                                                      self.resolutionParameters,
                                                                      self.uid)
            if ret is None:
                self.sigError.emit('Resolution ' + self.resolution + ' failed during run.')
            elif isinstance(ret, bool):
                # Resolution is running on the server, we do not have results right now.
                ret = None
        except Exception as e:
            self.sigError.emit('Resolution ' + self.resolution + ' failed during run: ' + str(e))
            ret = None

        # If the resolution is ran on the server or there is a problem, don't emit signal.
        if ret is not None and self.return_results:
            self.sig.emit(self.resolution, ret)
            self.done = True


class ResolutionParametersSelector(QtWidgets.QDialog):

    def __init__(self, properties: dict, includeEntitySelector: list = None, originTypes: list = None,
                 resolutionDescription: str = None) -> None:
        super(ResolutionParametersSelector, self).__init__()

        self.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)
        self.setModal(True)
        self.setWindowTitle('Resolution Wizard')
        self.parametersList = []
        # Have two separate dicts for readability.
        self.chosenParameters = {}
        self.parametersToRemember = {}

        dialogLayout = QtWidgets.QGridLayout()
        self.setLayout(dialogLayout)
        self.childWidget = QtWidgets.QTabWidget()
        dialogLayout.addWidget(self.childWidget, 0, 0, 4, 2)
        dialogLayout.setRowStretch(0, 1)
        dialogLayout.setColumnStretch(0, 1)

        if includeEntitySelector is not None and originTypes is not None:
            entitySelectTab = QtWidgets.QWidget()
            entitySelectTab.setLayout(QtWidgets.QVBoxLayout())
            labelText = ""
            if resolutionDescription is not None:
                labelText += resolutionDescription + "\n\n"
            labelText += 'Select the entities to use for this resolution.\nAccepted Origin Types: ' + \
                         ', '.join(originTypes)
            entitySelectTabLabel = QtWidgets.QLabel(labelText)
            entitySelectTabLabel.setWordWrap(True)
            entitySelectTabLabel.setMaximumWidth(600)

            entitySelectTabLabel.setAlignment(QtCore.Qt.AlignCenter)
            entitySelectTab.layout().addWidget(entitySelectTabLabel)

            self.entitySelector = QtWidgets.QListWidget()
            self.entitySelector.addItems(includeEntitySelector)

            self.entitySelector.setSelectionMode(self.entitySelector.MultiSelection)
            entitySelectTab.layout().addWidget(self.entitySelector)

            self.childWidget.addTab(entitySelectTab, 'Entities')

        for key in properties:
            propertyWidget = QtWidgets.QWidget()
            propertyKeyLayout = QtWidgets.QVBoxLayout()
            propertyWidget.setLayout(propertyKeyLayout)

            propertyLabel = QtWidgets.QLabel(properties[key].get('description'))
            propertyLabel.setWordWrap(True)
            propertyLabel.setMaximumWidth(600)

            propertyLabel.setAlignment(QtCore.Qt.AlignCenter)
            propertyKeyLayout.addWidget(propertyLabel)

            propertyType = properties[key].get('type')
            propertyValue = properties[key].get('value')
            propertyDefaultValue = properties[key].get('default')

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
                propertyInputField.setStyleSheet(Stylesheets.CHECK_BOX_STYLESHEET)

            rememberChoiceCheckbox = QtWidgets.QCheckBox('Remember Choice')
            rememberChoiceCheckbox.setStyleSheet(Stylesheets.CHECK_BOX_STYLESHEET)
            rememberChoiceCheckbox.setChecked(False)
            propertyKeyLayout.addWidget(rememberChoiceCheckbox)
            propertyKeyLayout.setStretch(1, 1)

            self.childWidget.addTab(propertyWidget, key)
            self.parametersList.append((key, propertyInputField, rememberChoiceCheckbox))

        nextButton = QtWidgets.QPushButton('Next')
        nextButton.setStyleSheet(Stylesheets.BUTTON_STYLESHEET_2)
        nextButton.clicked.connect(self.nextTab)
        previousButton = QtWidgets.QPushButton('Previous')
        previousButton.setStyleSheet(Stylesheets.BUTTON_STYLESHEET_2)
        previousButton.clicked.connect(self.previousTab)
        acceptButton = QtWidgets.QPushButton('Accept')
        acceptButton.setAutoDefault(True)
        acceptButton.setDefault(True)
        acceptButton.setStyleSheet(Stylesheets.BUTTON_STYLESHEET_2)
        acceptButton.clicked.connect(self.accept)
        cancelButton = QtWidgets.QPushButton('Cancel')
        cancelButton.setStyleSheet(Stylesheets.BUTTON_STYLESHEET_2)
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
        for resolutionParameterName, resolutionParameterInput, resolutionParameterRemember in self.parametersList:
            value = resolutionParameterInput.getValue()
            if value == '':
                msgBox = QtWidgets.QMessageBox()
                msgBox.setModal(True)
                QtWidgets.QMessageBox.warning(msgBox,
                                              "Not all parameters were filled in",
                                              "Some of the required parameters for the resolution have been left blank."
                                              " Please fill them in before proceeding.")
                return
            self.chosenParameters[resolutionParameterName] = value

            if resolutionParameterRemember.isChecked():
                self.parametersToRemember[resolutionParameterName] = value

        super(ResolutionParametersSelector, self).accept()


class GraphicsEditDialog(QtWidgets.QDialog):

    def __init__(self, settingsObject, resourceHandler):
        super(GraphicsEditDialog, self).__init__()

        self.setModal(True)
        self.setMaximumWidth(850)
        self.setMinimumWidth(600)
        self.setMaximumHeight(600)
        self.setMinimumHeight(400)
        self.settings = settingsObject
        self.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)

        editDialogLayout = QtWidgets.QGridLayout()
        self.setLayout(editDialogLayout)
        scrollArea = QtWidgets.QScrollArea()
        scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scrollArea.setWidgetResizable(True)
        scrollContainer = QtWidgets.QWidget()
        scrollLayout = QtWidgets.QVBoxLayout()
        scrollContainer.setLayout(scrollLayout)
        scrollArea.setWidget(scrollContainer)
        editDialogLayout.addWidget(scrollArea, 0, 0, 2, 2)

        resolutionCategoryWidget = QtWidgets.QWidget()
        self.resolutionCategoryLayout = SettingsCategoryLayout(supportsDeletion=False)
        resolutionCategoryWidget.setLayout(self.resolutionCategoryLayout)
        resolutionCategoryLabel = QtWidgets.QLabel('Graphics Settings')

        resolutionCategoryLabel.setFont(QtGui.QFont("Times", 13, QtGui.QFont.Bold))
        resolutionCategoryLabel.setFrameStyle(QtWidgets.QFrame.Raised | QtWidgets.QFrame.Panel)

        resolutionCategoryLabel.setAlignment(QtCore.Qt.AlignCenter)
        scrollLayout.addWidget(resolutionCategoryLabel)
        scrollLayout.addWidget(resolutionCategoryWidget)

        confirmButton = QtWidgets.QPushButton('Confirm')
        confirmButton.setStyleSheet(Stylesheets.BUTTON_STYLESHEET_2)
        confirmButton.clicked.connect(self.accept)
        editDialogLayout.addWidget(confirmButton, 2, 1, 1, 1)
        cancelButton = QtWidgets.QPushButton('Cancel')
        cancelButton.setStyleSheet(Stylesheets.BUTTON_STYLESHEET_2)
        cancelButton.clicked.connect(self.reject)
        editDialogLayout.addWidget(cancelButton, 2, 0, 1, 1)

        self.settingsTextboxes = []
        self.settingsValueTextboxes = []
        self.newSettings = {}

        etfSettingTextbox = SettingsIntegerEditTextBox(int(self.settings.value("Program/EntityTextFontSize")), "ETF",
                                                       50, 5)
        etfSettingTextbox.setStyleSheet(Stylesheets.TEXT_BOX_STYLESHEET)
        self.settingsValueTextboxes.append(etfSettingTextbox)
        self.resolutionCategoryLayout.addRow("Entity Text Font Size", etfSettingTextbox)

        ltfSettingTextbox = SettingsIntegerEditTextBox(int(self.settings.value("Program/LinkTextFontSize")), "LTF",
                                                       50, 5)
        ltfSettingTextbox.setStyleSheet(Stylesheets.TEXT_BOX_STYLESHEET)
        self.settingsValueTextboxes.append(ltfSettingTextbox)
        self.resolutionCategoryLayout.addRow("Link Text Font Size", ltfSettingTextbox)

        self.colorPicker = QtWidgets.QColorDialog()
        self.colorPicker.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)
        self.colorPicker.setOption(QtWidgets.QColorDialog.DontUseNativeDialog, True)

        etcSettingWidget = QtWidgets.QWidget()
        etcSettingLayout = QtWidgets.QHBoxLayout()
        etcSettingWidget.setLayout(etcSettingLayout)

        etcSettingTextbox = SettingsEditTextBox(self.settings.value("Program/EntityTextColor"), "ETC")
        etcSettingTextbox.setReadOnly(True)
        etcSettingTextbox.setStyleSheet(Stylesheets.TEXT_BOX_STYLESHEET)
        etcSettingLayout.addWidget(etcSettingTextbox, 5)

        etcSettingPalettePrompt = QtWidgets.QPushButton(QtGui.QIcon(resourceHandler.getIcon("colorPicker")),
                                                        "Pick Colour")
        etcSettingPalettePrompt.clicked.connect(self.runEntityColorPicker)
        etcSettingLayout.addWidget(etcSettingPalettePrompt)

        self.settingsTextboxes.append(etcSettingTextbox)
        self.resolutionCategoryLayout.addRow("Entity Text Color", etcSettingWidget)

        ltcSettingWidget = QtWidgets.QWidget()
        ltcSettingLayout = QtWidgets.QHBoxLayout()
        ltcSettingWidget.setLayout(ltcSettingLayout)

        ltcSettingTextbox = SettingsEditTextBox(self.settings.value("Program/LinkTextColor"), "LTC")
        ltcSettingTextbox.setReadOnly(True)
        ltcSettingTextbox.setStyleSheet(Stylesheets.TEXT_BOX_STYLESHEET)
        ltcSettingLayout.addWidget(ltcSettingTextbox, 5)

        ltcSettingPalettePrompt = QtWidgets.QPushButton(QtGui.QIcon(resourceHandler.getIcon("colorPicker")),
                                                        "Pick Colour")
        ltcSettingPalettePrompt.clicked.connect(self.runLinkColorPicker)
        ltcSettingLayout.addWidget(ltcSettingPalettePrompt)

        self.settingsTextboxes.append(ltcSettingTextbox)
        self.resolutionCategoryLayout.addRow("Link Text Color", ltcSettingWidget)

    def runEntityColorPicker(self):
        color = self.colorPicker.getColor(QtGui.QColor(self.settings.value("Program/EntityTextColor")),
                                          title="Select New Entity Text Color")
        if color.isValid():
            self.settingsTextboxes[0].setText(color.name())

    def runLinkColorPicker(self):
        color = self.colorPicker.getColor(QtGui.QColor(self.settings.value("Program/LinkTextColor")),
                                          title="Select New Link Text Color")
        if color.isValid():
            self.settingsTextboxes[1].setText(color.name())

    def accept(self) -> None:
        # Cannot delete these values.
        for settingTextbox in self.settingsTextboxes:
            key = settingTextbox.settingsKey
            value = settingTextbox.text()
            self.newSettings[key] = value
        for settingsValueTextbox in self.settingsValueTextboxes:
            key = settingsValueTextbox.settingsKey
            value = settingsValueTextbox.value()
            self.newSettings[key] = value

        super(GraphicsEditDialog, self).accept()


class ProgramEditDialog(QtWidgets.QDialog):

    def __init__(self, settingsObject):
        super(ProgramEditDialog, self).__init__()
        self.setModal(True)
        self.setMaximumWidth(850)
        self.setMinimumWidth(600)
        self.setMaximumHeight(600)
        self.setMinimumHeight(400)
        self.settings = settingsObject
        self.setStyleSheet(Stylesheets.MENUS_STYLESHEET)

        resolutionsEditDialog = QtWidgets.QGridLayout()
        self.setLayout(resolutionsEditDialog)
        scrollArea = QtWidgets.QScrollArea()
        scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scrollArea.setWidgetResizable(True)
        scrollContainer = QtWidgets.QWidget()
        scrollLayout = QtWidgets.QVBoxLayout()
        scrollContainer.setLayout(scrollLayout)
        scrollArea.setWidget(scrollContainer)
        resolutionsEditDialog.addWidget(scrollArea, 0, 0, 2, 2)

        resolutionCategoryWidget = QtWidgets.QWidget()
        self.resolutionCategoryLayout = SettingsCategoryLayout()
        resolutionCategoryWidget.setLayout(self.resolutionCategoryLayout)
        resolutionCategoryLabel = QtWidgets.QLabel('Program Settings')

        resolutionCategoryLabel.setFont(QtGui.QFont("Times", 13, QtGui.QFont.Bold))
        resolutionCategoryLabel.setFrameStyle(QtWidgets.QFrame.Raised | QtWidgets.QFrame.Panel)

        resolutionCategoryLabel.setAlignment(QtCore.Qt.AlignCenter)
        scrollLayout.addWidget(resolutionCategoryLabel)
        scrollLayout.addWidget(resolutionCategoryWidget)

        confirmButton = QtWidgets.QPushButton('Confirm')
        confirmButton.setStyleSheet(Stylesheets.BUTTON_STYLESHEET_2)
        confirmButton.clicked.connect(self.accept)
        resolutionsEditDialog.addWidget(confirmButton, 2, 1, 1, 1)
        cancelButton = QtWidgets.QPushButton('Cancel')
        cancelButton.setStyleSheet(Stylesheets.BUTTON_STYLESHEET_2)
        cancelButton.clicked.connect(self.reject)
        resolutionsEditDialog.addWidget(cancelButton, 2, 0, 1, 1)

        self.settingsTextboxes = []
        self.newSettings = {}
        self.settingsSingleChoice = []

        for setting in self.settings:
            if setting.startswith('Program/'):
                keyName = setting.split('Program/', 1)[1]
                if keyName != "BaseDir":  # Don't allow users to mess with this.
                    # A bit redundant to do it this way, but it'll be cleaner if / when more settings are added.
                    if keyName == "GraphLayout":
                        settingSingleChoice = SettingsEditSingleChoice(['dot', 'sfdp', 'neato'],
                                                                       self.settings.value(setting),
                                                                       setting)
                        settingSingleChoice.setStyleSheet(Stylesheets.RADIO_BUTTON_STYLESHEET)
                        self.settingsSingleChoice.append(settingSingleChoice)
                        self.resolutionCategoryLayout.addRow(keyName, settingSingleChoice)
                    else:
                        settingTextbox = SettingsEditTextBox(self.settings.value(setting), setting)
                        self.settingsTextboxes.append(settingTextbox)
                        self.resolutionCategoryLayout.addRow(keyName, settingTextbox)

    def accept(self) -> None:
        for settingTextbox in self.settingsTextboxes:
            key = settingTextbox.settingsKey
            value = settingTextbox.text()
            isDeleted = settingTextbox.keyDeleted
            self.newSettings[key] = (value, isDeleted)
        for settingSingleChoice in self.settingsSingleChoice:
            key = settingSingleChoice.settingsKey
            value = [option.text() for option in settingSingleChoice.options if option.isChecked()][0]
            isDeleted = settingSingleChoice.keyDeleted
            self.newSettings[key] = (value, isDeleted)

        super(ProgramEditDialog, self).accept()


class ResolutionsEditDialog(QtWidgets.QDialog):

    def __init__(self, settingsObject):
        super(ResolutionsEditDialog, self).__init__()
        self.setModal(True)
        self.setMaximumWidth(850)
        self.setMinimumWidth(600)
        self.setMaximumHeight(600)
        self.setMinimumHeight(400)
        self.settings = settingsObject
        self.setStyleSheet(Stylesheets.MENUS_STYLESHEET)

        resolutionsEditDialog = QtWidgets.QGridLayout()
        self.setLayout(resolutionsEditDialog)
        scrollArea = QtWidgets.QScrollArea()
        scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scrollArea.setWidgetResizable(True)
        scrollContainer = QtWidgets.QWidget()
        scrollLayout = QtWidgets.QVBoxLayout()
        scrollContainer.setLayout(scrollLayout)
        scrollArea.setWidget(scrollContainer)
        resolutionsEditDialog.addWidget(scrollArea, 0, 0, 2, 2)

        resolutionCategoryWidget = QtWidgets.QWidget()
        self.resolutionCategoryLayout = SettingsCategoryLayout()
        resolutionCategoryWidget.setLayout(self.resolutionCategoryLayout)
        resolutionCategoryLabel = QtWidgets.QLabel('Resolutions Settings')

        resolutionCategoryLabel.setFont(QtGui.QFont("Times", 13, QtGui.QFont.Bold))
        resolutionCategoryLabel.setFrameStyle(QtWidgets.QFrame.Raised | QtWidgets.QFrame.Panel)

        resolutionCategoryLabel.setAlignment(QtCore.Qt.AlignCenter)
        scrollLayout.addWidget(resolutionCategoryLabel)
        scrollLayout.addWidget(resolutionCategoryWidget)

        confirmButton = QtWidgets.QPushButton('Confirm')
        confirmButton.setStyleSheet(Stylesheets.BUTTON_STYLESHEET_2)
        confirmButton.clicked.connect(self.accept)
        resolutionsEditDialog.addWidget(confirmButton, 2, 1, 1, 1)
        cancelButton = QtWidgets.QPushButton('Cancel')
        cancelButton.setStyleSheet(Stylesheets.BUTTON_STYLESHEET_2)
        cancelButton.clicked.connect(self.reject)
        resolutionsEditDialog.addWidget(cancelButton, 2, 0, 1, 1)

        self.settingsTextboxes = []
        self.newSettings = {}

        for setting in self.settings:
            settingTextbox = SettingsEditTextBox(self.settings.value(setting), setting)
            self.settingsTextboxes.append(settingTextbox)

            if setting.startswith('Resolutions/'):
                keyName = setting.split('Resolutions/', 1)[1]
                self.resolutionCategoryLayout.addRow(keyName, settingTextbox)

    def accept(self) -> None:
        for settingTextbox in self.settingsTextboxes:
            key = settingTextbox.settingsKey
            value = settingTextbox.text()
            isDeleted = settingTextbox.keyDeleted
            self.newSettings[key] = (value, isDeleted)

        super(ResolutionsEditDialog, self).accept()


class LoggingSettingsDialog(QtWidgets.QDialog):

    def __init__(self, settingsObject):
        super(LoggingSettingsDialog, self).__init__()

        self.setModal(True)
        self.setMaximumWidth(850)
        self.setMinimumWidth(600)
        self.setMaximumHeight(600)
        self.setMinimumHeight(400)
        self.settings = settingsObject
        self.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)

        loggingSettingsLayout = QtWidgets.QGridLayout()
        self.setLayout(loggingSettingsLayout)
        scrollArea = QtWidgets.QScrollArea()
        scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scrollArea.setWidgetResizable(True)
        scrollContainer = QtWidgets.QWidget()
        scrollLayout = QtWidgets.QVBoxLayout()
        scrollContainer.setLayout(scrollLayout)
        scrollArea.setWidget(scrollContainer)
        loggingSettingsLayout.addWidget(scrollArea, 0, 0, 2, 2)

        # Settings Categories: Program, Logging, Project, Resolution, Other.

        loggingCategoryWidget = QtWidgets.QWidget()
        self.loggingCategoryLayout = SettingsCategoryLayout(supportsDeletion=False)
        loggingCategoryWidget.setLayout(self.loggingCategoryLayout)
        loggingCategoryLabel = QtWidgets.QLabel('Logging Settings')

        loggingCategoryLabel.setFont(QtGui.QFont("Times", 13, QtGui.QFont.Bold))
        loggingCategoryLabel.setFrameStyle(QtWidgets.QFrame.Raised | QtWidgets.QFrame.Panel)

        loggingCategoryLabel.setAlignment(QtCore.Qt.AlignCenter)
        scrollLayout.addWidget(loggingCategoryLabel)
        scrollLayout.addWidget(loggingCategoryWidget)

        confirmButton = QtWidgets.QPushButton('Confirm')
        confirmButton.setStyleSheet(Stylesheets.BUTTON_STYLESHEET_2)
        confirmButton.clicked.connect(self.accept)
        loggingSettingsLayout.addWidget(confirmButton, 2, 1, 1, 1)
        cancelButton = QtWidgets.QPushButton('Cancel')
        cancelButton.setStyleSheet(Stylesheets.BUTTON_STYLESHEET_2)
        cancelButton.clicked.connect(self.reject)
        loggingSettingsLayout.addWidget(cancelButton, 2, 0, 1, 1)

        self.settingsTextboxes = []
        self.newSettings = {}

        for setting in self.settings:
            settingTextbox = SettingsEditTextBox(self.settings.value(setting), setting)
            settingTextbox.setStyleSheet(Stylesheets.TEXT_BOX_STYLESHEET)
            self.settingsTextboxes.append(settingTextbox)
            if setting.startswith('Logging/'):
                keyName = setting.split('Logging/', 1)[1]
                self.loggingCategoryLayout.addRow(keyName, settingTextbox)

    def accept(self) -> None:
        for settingTextbox in self.settingsTextboxes:
            key = settingTextbox.settingsKey
            value = settingTextbox.text()
            isDeleted = settingTextbox.keyDeleted
            self.newSettings[key] = (value, isDeleted)

        super(LoggingSettingsDialog, self).accept()


class ProjectEditDialog(QtWidgets.QDialog):

    def __init__(self, settingsObject):
        super(ProjectEditDialog, self).__init__()

        self.setModal(True)
        self.setMaximumWidth(850)
        self.setMinimumWidth(600)
        self.setMaximumHeight(600)
        self.setMinimumHeight(400)
        self.settings = settingsObject
        self.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)

        editDialogLayout = QtWidgets.QGridLayout()
        self.setLayout(editDialogLayout)
        scrollArea = QtWidgets.QScrollArea()
        scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scrollArea.setWidgetResizable(True)
        scrollContainer = QtWidgets.QWidget()
        scrollLayout = QtWidgets.QVBoxLayout()
        scrollContainer.setLayout(scrollLayout)
        scrollArea.setWidget(scrollContainer)
        editDialogLayout.addWidget(scrollArea, 0, 0, 2, 2)

        resolutionCategoryWidget = QtWidgets.QWidget()
        self.resolutionCategoryLayout = SettingsCategoryLayout(supportsDeletion=False)
        resolutionCategoryWidget.setLayout(self.resolutionCategoryLayout)
        resolutionCategoryLabel = QtWidgets.QLabel('Project Settings')

        resolutionCategoryLabel.setFont(QtGui.QFont("Times", 13, QtGui.QFont.Bold))
        resolutionCategoryLabel.setFrameStyle(QtWidgets.QFrame.Raised | QtWidgets.QFrame.Panel)

        resolutionCategoryLabel.setAlignment(QtCore.Qt.AlignCenter)
        scrollLayout.addWidget(resolutionCategoryLabel)
        scrollLayout.addWidget(resolutionCategoryWidget)

        confirmButton = QtWidgets.QPushButton('Confirm')
        confirmButton.setStyleSheet(Stylesheets.BUTTON_STYLESHEET_2)
        confirmButton.clicked.connect(self.accept)
        editDialogLayout.addWidget(confirmButton, 2, 1, 1, 1)
        cancelButton = QtWidgets.QPushButton('Cancel')
        cancelButton.setStyleSheet(Stylesheets.BUTTON_STYLESHEET_2)
        cancelButton.clicked.connect(self.reject)
        editDialogLayout.addWidget(cancelButton, 2, 0, 1, 1)

        self.settingsTextboxes = []
        self.settingsSingleChoice = []
        self.newSettings = {}

        for setting in self.settings:
            if setting == 'Project/Resolution Result Grouping Threshold' or \
                    setting == 'Project/Number of Answers Returned' or \
                    setting == 'Project/Question Answering Retriever Value' or \
                    setting == 'Project/Question Answering Reader Value':
                keyName = setting.split('Project/', 1)[1]
                settingTextbox = SettingsEditTextBox(self.settings.value(setting), setting)
                settingTextbox.setStyleSheet(Stylesheets.TEXT_BOX_STYLESHEET)
                self.settingsTextboxes.append(settingTextbox)
                self.resolutionCategoryLayout.addRow(keyName, settingTextbox)

            elif setting == 'Project/Symlink or Copy Materials':
                keyName = setting.split('Project/', 1)[1]
                settingSingleChoice = SettingsEditSingleChoice(['Symlink', 'Copy'], self.settings.value(setting),
                                                               setting)
                settingSingleChoice.setStyleSheet(Stylesheets.RADIO_BUTTON_STYLESHEET)
                self.settingsSingleChoice.append(settingSingleChoice)
                self.resolutionCategoryLayout.addRow(keyName, settingSingleChoice)

    def accept(self) -> None:
        for settingTextbox in self.settingsTextboxes:
            key = settingTextbox.settingsKey
            value = settingTextbox.text()
            isDeleted = settingTextbox.keyDeleted
            self.newSettings[key] = (value, isDeleted)
        for settingSingleChoice in self.settingsSingleChoice:
            key = settingSingleChoice.settingsKey
            value = [option.text() for option in settingSingleChoice.options if option.isChecked()][0]
            isDeleted = settingSingleChoice.keyDeleted
            self.newSettings[key] = (value, isDeleted)

        super(ProjectEditDialog, self).accept()


class SettingsEditTextBox(QtWidgets.QLineEdit):

    def __init__(self, contents: str, settingsKey: str):
        super(SettingsEditTextBox, self).__init__(str(contents))
        self.settingsKey = settingsKey
        self.keyDeleted = False
        self.setToolTip("Edit the contents to change the setting's value.")


class SettingsIntegerEditTextBox(QtWidgets.QSpinBox):

    def __init__(self, contents: int, settingsKey: str, maxVal: int, minVal: int):
        super(SettingsIntegerEditTextBox, self).__init__()
        self.setMaximum(maxVal)
        self.setMinimum(minVal)
        self.setValue(contents)
        self.settingsKey = settingsKey
        self.keyDeleted = False
        self.setToolTip("Edit the contents to change the setting's value.")


class SettingsEditSingleChoice(QtWidgets.QWidget):

    def __init__(self, contents, currentSettingValue, settingsKey):
        super(SettingsEditSingleChoice, self).__init__()
        self.settingsKey = settingsKey
        self.keyDeleted = False
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        self.options = []

        for userChoice in contents:
            radioButton = QtWidgets.QRadioButton(userChoice)
            self.options.append(radioButton)
            if userChoice == currentSettingValue:
                radioButton.setChecked(True)
            self.layout().addWidget(radioButton)


class SettingsCategoryLayout(QtWidgets.QVBoxLayout):

    def __init__(self, supportsDeletion: bool = True):
        super(SettingsCategoryLayout, self).__init__()
        self.supportsDeletion = supportsDeletion

    def addRow(self, labelText: str, valueWidget):
        rowWidget = QtWidgets.QWidget()
        rowWidgetLayout = QtWidgets.QVBoxLayout()
        rowWidget.setLayout(rowWidgetLayout)
        keyLabel = QtWidgets.QLabel(labelText)

        keyLabel.setAlignment(QtCore.Qt.AlignCenter)
        rowWidgetLayout.addWidget(keyLabel)
        rowWidgetLayout.addWidget(valueWidget)
        if self.supportsDeletion:
            deleteKeyButton = SettingsDeleteKeyButton('Delete', valueWidget, rowWidget)
            rowWidgetLayout.addWidget(deleteKeyButton)
        self.addWidget(rowWidget)


class SettingsDeleteKeyButton(QtWidgets.QPushButton):

    def __init__(self, text: str, settingsItem, rowItem: QtWidgets.QWidget):
        super(SettingsDeleteKeyButton, self).__init__(text)
        self.settingsItem = settingsItem
        self.rowItem = rowItem

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self.settingsItem.keyDeleted = True
        self.rowItem.hide()


class FindEntityOnCanvasDialog(QtWidgets.QDialog):

    def __init__(self, primaryFieldsList: list, regex: bool):
        super(FindEntityOnCanvasDialog, self).__init__()
        self.setModal(True)
        self.setMinimumWidth(400)
        if regex:
            self.setWindowTitle('Regex Find Entity or Link')
        else:
            self.setWindowTitle('Find Entity or Link')
        self.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)

        findLabel = QtWidgets.QLabel('Find:')

        findLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.findInput = QtWidgets.QLineEdit('')
        self.findInput.setPlaceholderText('Type the primary field value to search for')

        confirmButton = QtWidgets.QPushButton('Confirm')
        confirmButton.setStyleSheet(Stylesheets.BUTTON_STYLESHEET_2)
        confirmButton.clicked.connect(self.accept)
        cancelButton = QtWidgets.QPushButton('Cancel')
        cancelButton.setStyleSheet(Stylesheets.BUTTON_STYLESHEET_2)
        cancelButton.clicked.connect(self.reject)

        autoCompleter = QtWidgets.QCompleter(primaryFieldsList)
        if regex:
            # Doesn't actually work in python, as far as I can see.
            # Throws error:  Unhandled QCompleter::filterMode flag is used.
            # autoCompleter.setFilterMode(QtGui.Qt.MatchRegularExpression)
            pass
        else:
            autoCompleter.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
            autoCompleter.setFilterMode(QtCore.Qt.MatchContains)
        self.findInput.setCompleter(autoCompleter)

        findLayout = QtWidgets.QGridLayout()
        self.setLayout(findLayout)

        findLayout.addWidget(findLabel, 0, 0, 1, 1)
        findLayout.addWidget(self.findInput, 0, 1, 1, 1)
        # Adding the confirm button first so that it's what is activated when someone presses Enter.
        findLayout.addWidget(confirmButton, 1, 1, 1, 1)
        findLayout.addWidget(cancelButton, 1, 0, 1, 1)


class FindEntityOfTypeOnCanvasDialog(QtWidgets.QDialog):

    def __init__(self, entityTypesDict: dict, regex: bool):
        super(FindEntityOfTypeOnCanvasDialog, self).__init__()
        self.setModal(True)
        self.setMinimumWidth(400)
        if regex:
            self.setWindowTitle('Regex Find Entity Of Type')
        else:
            self.setWindowTitle('Find Entity Of Type')
        self.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)

        typeLabel = QtWidgets.QLabel('Entity Type:')
        self.typeInput = QtWidgets.QComboBox()
        self.typeInput.setEditable(False)
        self.typeInput.addItems(list(entityTypesDict))
        self.typeInput.currentIndexChanged.connect(self.changeSelectedType)
        findLabel = QtWidgets.QLabel('Find Entity:')

        findLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.findInput = QtWidgets.QLineEdit('')
        self.findInput.setPlaceholderText('Type the primary field value to search for')

        confirmButton = QtWidgets.QPushButton('Confirm')
        confirmButton.setStyleSheet(Stylesheets.BUTTON_STYLESHEET_2)
        confirmButton.clicked.connect(self.accept)
        cancelButton = QtWidgets.QPushButton('Cancel')
        cancelButton.setStyleSheet(Stylesheets.BUTTON_STYLESHEET_2)
        cancelButton.clicked.connect(self.reject)

        self.autoCompleters = {}
        for entityType in entityTypesDict:
            autoCompleter = QtWidgets.QCompleter(list(entityTypesDict[entityType]))
            self.autoCompleters[entityType] = autoCompleter
            if regex:
                # Doesn't actually work in python, as far as I can see.
                # Throws error:  Unhandled QCompleter::filterMode flag is used.
                # autoCompleter.setFilterMode(QtGui.Qt.MatchRegularExpression)
                pass
            else:
                autoCompleter.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
                autoCompleter.setFilterMode(QtCore.Qt.MatchContains)

        findLayout = QtWidgets.QGridLayout()
        self.setLayout(findLayout)

        findLayout.addWidget(typeLabel, 0, 0, 1, 1)
        findLayout.addWidget(self.typeInput, 0, 1, 1, 1)
        findLayout.addWidget(findLabel, 1, 0, 1, 1)
        findLayout.addWidget(self.findInput, 1, 1, 1, 1)
        # Adding the confirm button first so that it's what is activated when someone presses Enter.
        findLayout.addWidget(confirmButton, 2, 1, 1, 1)
        findLayout.addWidget(cancelButton, 2, 0, 1, 1)

        self.changeSelectedType()

    def changeSelectedType(self):
        self.findInput.setCompleter(self.autoCompleters[self.typeInput.currentText()])


class ResolutionSearchResultsList(QtWidgets.QListWidget):

    def __init__(self, mainWindowObject: MainWindow):
        super(ResolutionSearchResultsList, self).__init__()
        self.mainWindow = mainWindowObject

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        super(ResolutionSearchResultsList, self).mouseDoubleClickEvent(event)
        resItem = self.itemAt(event.pos())
        if resItem is None or '/' not in resItem.text():
            return
        self.mainWindow.centralWidget().tabbedPane.getCurrentScene().clearSelection()
        self.mainWindow.runResolution(resItem.text())


class FindResolutionDialog(QtWidgets.QDialog):

    def __init__(self, parent: MainWindow, entityList: list, resolutionDict: dict):
        super(FindResolutionDialog, self).__init__()
        self.entities = entityList
        self.resolutions = resolutionDict
        self.setModal(True)
        self.setWindowTitle('Find Resolutions')
        self.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)

        dialogLayout = QtWidgets.QGridLayout()
        self.setLayout(dialogLayout)

        descriptionLabel = QtWidgets.QLabel("Find Resolutions based on their parameters.")
        descriptionLabel.setWordWrap(True)
        dialogLayout.addWidget(descriptionLabel, 0, 0, 1, 2)

        originLabel = QtWidgets.QLabel("Origin Entity:")
        self.originDropDown = QtWidgets.QComboBox()
        self.originDropDown.addItem('Any')
        self.originDropDown.addItems(entityList)
        self.originDropDown.addItem('*')
        dialogLayout.addWidget(originLabel, 1, 0, 1, 1)
        dialogLayout.addWidget(self.originDropDown, 1, 1, 1, 1)

        targetLabel = QtWidgets.QLabel("Target Entity:")
        self.targetDropDown = QtWidgets.QComboBox()
        self.targetDropDown.addItem('Any')
        self.targetDropDown.addItems(entityList)
        self.targetDropDown.addItem('*')
        dialogLayout.addWidget(targetLabel, 2, 0, 1, 1)
        dialogLayout.addWidget(self.targetDropDown, 2, 1, 1, 1)

        keywordsLabel = QtWidgets.QLabel("Keywords:")
        self.keywordsWidget = QtWidgets.QLineEdit()
        self.keywordsWidget.setToolTip("Add keywords separated by spaces.\nKeywords are checked against the "
                                       "resolutions' titles and descriptions.")
        dialogLayout.addWidget(keywordsLabel, 3, 0, 1, 2)
        dialogLayout.addWidget(self.keywordsWidget, 4, 0, 1, 2)

        resultsLabel = QtWidgets.QLabel("Matches:")
        self.resultsWidget = ResolutionSearchResultsList(parent)
        self.resultsWidget.addItem('Click "Search" to display results')
        dialogLayout.addWidget(resultsLabel, 5, 0, 1, 2)
        dialogLayout.addWidget(self.resultsWidget, 6, 0, 2, 2)

        self.searchButton = QtWidgets.QPushButton("Search")
        self.searchButton.clicked.connect(self.search)
        self.closeButton = QtWidgets.QPushButton("Close")
        self.closeButton.clicked.connect(self.accept)
        dialogLayout.addWidget(self.closeButton, 8, 0, 1, 1)
        dialogLayout.addWidget(self.searchButton, 8, 1, 1, 1)

    def search(self):
        self.resultsWidget.clear()
        target = self.targetDropDown.currentText()
        validResolutions = []
        if target != 'Any':
            for category in self.resolutions:
                for resolution in self.resolutions[category]:
                    if target in self.resolutions[category][resolution]['originTypes']:
                        validResolutions.append(category + '/' + resolution)
        else:
            for category in self.resolutions:
                for resolution in self.resolutions[category]:
                    validResolutions.append(category + '/' + resolution)

        origin = self.originDropDown.currentText()
        if origin != 'Any':
            for category in self.resolutions:
                for resolution in self.resolutions[category]:
                    if origin not in self.resolutions[category][resolution]['originTypes']:
                        try:
                            validResolutions.remove(str(category) + '/' + str(resolution))
                        except KeyError:
                            # Python's philosophy of asking for forgiveness instead of asking for permission
                            #   is not one to live your life by. When in Rome, though.
                            pass

        # Try to see if any of the keywords are a substring of the name or description of any resolution.
        keywordFilter = self.keywordsWidget.text().strip()
        if keywordFilter != '':
            wordsToFind = keywordFilter.split(' ')
            for category in self.resolutions:
                for resolution in self.resolutions[category]:
                    titleText = self.resolutions[category][resolution]['name']
                    descriptionText = self.resolutions[category][resolution]['description']
                    for keyword in wordsToFind:
                        if keyword not in titleText and keyword not in descriptionText:
                            try:
                                validResolutions.remove(str(category) + '/' + str(resolution))
                            except KeyError:
                                pass

        for result in validResolutions:
            self.resultsWidget.addItem(result)


class MergeEntitiesDialog(QtWidgets.QDialog):

    def __init__(self, parent: MainWindow, entitiesToMerge: list):
        super(MergeEntitiesDialog, self).__init__()
        self.setModal(True)
        self.setWindowTitle('Merge Entities')
        self.parent = parent
        self.entitiesToMerge = entitiesToMerge
        self.primaryEntityUID = None
        self.otherEntitiesUIDs = []
        self.setStyleSheet(Stylesheets.MERGE_STYLESHEET)

        descriptionLabel = QtWidgets.QLabel("Select the primary entity onto which the fields of the "
                                            "other entities will be merged. The order in which the "
                                            "entities are in the table is the order in which they will "
                                            "be merged. The first entity is written first. Fields with "
                                            "non 'None' values are not overwritten.")
        descriptionLabel.setWordWrap(True)

        dialogLayout = QtWidgets.QGridLayout()
        self.setLayout(dialogLayout)
        self.entitiesTable = MergeTableWidget(0, 5, self)
        self.entitiesTable.setHorizontalHeaderLabels(['Entity', 'Entity Type', 'Incoming\nLinks',
                                                      'Outgoing\nLinks', 'Shift\nPriority'])

        self.radioButtonGroup = QtWidgets.QButtonGroup()

        for entity in entitiesToMerge:
            self.insertRow(entity)

        self.entitiesTable.cellWidget(0, 0).setChecked(True)
        self.entitiesTable.setColumnWidth(0, 150)
        self.entitiesTable.setColumnWidth(1, 150)
        self.entitiesTable.setMinimumWidth(self.entitiesTable.width())

        dialogLayout.addWidget(descriptionLabel, 0, 0, 2, 2)
        dialogLayout.addWidget(self.entitiesTable, 2, 0, 2, 2)
        dialogLayout.setRowStretch(3, 1)

        acceptButton = QtWidgets.QPushButton('Accept')
        acceptButton.setStyleSheet(Stylesheets.BUTTON_STYLESHEET_2)
        cancelButton = QtWidgets.QPushButton('Cancel')
        cancelButton.setStyleSheet(Stylesheets.BUTTON_STYLESHEET_2)
        acceptButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)
        dialogLayout.addWidget(cancelButton, 4, 0, 1, 1)
        dialogLayout.addWidget(acceptButton, 4, 1, 1, 1)

        self.adjustSize()
        self.setFixedWidth(self.entitiesTable.width() + 19)
        self.setMaximumHeight(700)

    def insertRow(self, entityJSON):
        newRowIndex = self.entitiesTable.rowCount()
        self.entitiesTable.insertRow(newRowIndex)
        self.entitiesTable.setRowHeight(newRowIndex, 70)
        isPrimaryRadioButton = QtWidgets.QRadioButton()
        isPrimaryRadioButton.setStyleSheet(Stylesheets.RADIO_BUTTON_STYLESHEET)
        isPrimaryRadioButton.setText(entityJSON[list(entityJSON)[1]])

        self.entitiesTable.setCellWidget(newRowIndex, 0, isPrimaryRadioButton)

        pixmapLabel = QtWidgets.QLabel()
        entityPixmap = QtGui.QPixmap()
        entityPixmap.loadFromData(entityJSON.get('Icon'))
        pixmapLabel.setPixmap(entityPixmap)

        pixmapLabel.setAlignment(QtCore.Qt.AlignCenter)
        entityTypeWidget = QtWidgets.QWidget()
        entityTypeWidgetLayout = QtWidgets.QHBoxLayout()
        entityTypeWidget.setLayout(entityTypeWidgetLayout)
        entityTypeWidgetLayout.addWidget(pixmapLabel)
        entityTypeWidgetLayout.addWidget(QtWidgets.QLabel(entityJSON['Entity Type']))

        self.entitiesTable.setCellWidget(newRowIndex, 1, entityTypeWidget)

        incomingLinks = QtWidgets.QLabel(str(len(self.parent.LENTDB.getIncomingLinks(entityJSON['uid']))))

        incomingLinks.setAlignment(QtCore.Qt.AlignCenter)
        self.entitiesTable.setCellWidget(newRowIndex, 2, incomingLinks)
        outgoingLinks = QtWidgets.QLabel(str(len(self.parent.LENTDB.getOutgoingLinks(entityJSON['uid']))))

        outgoingLinks.setAlignment(QtCore.Qt.AlignCenter)
        self.entitiesTable.setCellWidget(newRowIndex, 3, outgoingLinks)

        upDownButtons = MergeTableShiftRowUpDownButtons(self.entitiesTable, entityJSON['uid'])

        self.entitiesTable.setCellWidget(newRowIndex, 4, upDownButtons)

    def accept(self) -> None:
        for rowIndex in range(0, self.entitiesTable.rowCount()):
            if self.entitiesTable.cellWidget(rowIndex, 0).isChecked():
                self.primaryEntityUID = self.entitiesTable.cellWidget(rowIndex, 4).uid
            else:
                self.otherEntitiesUIDs.append(self.entitiesTable.cellWidget(rowIndex, 4).uid)
        super(MergeEntitiesDialog, self).accept()


class MergeTableWidget(QtWidgets.QTableWidget):
    """
    Table that presents the user the selected entities for them to merge.

    The user will select a primary entity, and reorder the table such that the most important
    entity values to preserve will be in entities at the top of the table.

    The table has 5 columns, and indices for columns go from 0 to 4.
    """

    def findRowOfShiftingWidget(self, widget: QtWidgets.QWidget):
        # Always in column with index 4.
        for row in range(self.rowCount()):
            if self.cellWidget(row, 4) == widget:
                return row

    def shiftRowUp(self, widget: QtWidgets.QWidget):
        rowIndex = self.findRowOfShiftingWidget(widget)
        if rowIndex == 0:
            return rowIndex
        widgetsToShift = []
        for widgetColumnIndex in range(5):
            widgetsToShift.append(self.cellWidget(rowIndex, widgetColumnIndex))
        self.insertRow(rowIndex - 1)
        self.setRowHeight(rowIndex - 1, 70)
        for widgetColumnIndex in range(5):
            self.setCellWidget(rowIndex - 1, widgetColumnIndex, widgetsToShift[widgetColumnIndex])
        self.removeRow(rowIndex + 1)

    def shiftRowDown(self, widget: QtWidgets.QWidget) -> None:
        rowIndex = self.findRowOfShiftingWidget(widget)
        if rowIndex == self.rowCount() - 1:
            return
        widgetsToShift = []
        for widgetColumnIndex in range(5):
            widgetsToShift.append(self.cellWidget(rowIndex, widgetColumnIndex))
        self.insertRow(rowIndex + 2)
        self.setRowHeight(rowIndex + 2, 70)
        for widgetColumnIndex in range(5):
            self.setCellWidget(rowIndex + 2, widgetColumnIndex, widgetsToShift[widgetColumnIndex])
        self.removeRow(rowIndex)


class MergeTableShiftRowUpDownButtons(QtWidgets.QWidget):

    def __init__(self, parent, uid) -> None:
        super(MergeTableShiftRowUpDownButtons, self).__init__(parent=parent)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.uid = uid

        upButton = QtWidgets.QPushButton('^')
        upButton.setStyleSheet(Stylesheets.BUTTON_STYLESHEET)

        downButton = QtWidgets.QPushButton('v')
        downButton.setStyleSheet(Stylesheets.BUTTON_STYLESHEET)

        upButton.clicked.connect(lambda: self.shiftRow(True))
        downButton.clicked.connect(lambda: self.shiftRow(False))

        self.layout().addWidget(upButton)
        self.layout().addWidget(downButton)

    def shiftRow(self, shiftUp: bool) -> None:
        if shiftUp:
            self.parent().parent().shiftRowUp(self)
        else:
            self.parent().parent().shiftRowDown(self)


class SplitEntitiesDialog(QtWidgets.QDialog):

    def __init__(self, parent: MainWindow, entityToSplit: dict) -> None:
        super(SplitEntitiesDialog, self).__init__()
        self.setModal(True)
        self.parent = parent
        self.entityToSplitPrimaryField = entityToSplit[list(entityToSplit)[1]]
        self.setWindowTitle('Split Entities')
        # One is used to store primary fields, the other primary fields + the links that the user selected
        # for that primary field. This takes up more memory, but less processing time.
        self.splitEntities = []
        self.splitEntitiesWithLinks = []
        self.setStyleSheet(Stylesheets.MERGE_STYLESHEET)

        incomingLinks = list(parent.LENTDB.getIncomingLinks(entityToSplit['uid']))
        outgoingLinks = list(parent.LENTDB.getOutgoingLinks(entityToSplit['uid']))
        self.allLinks = [parent.LENTDB.getLink(linkUID) for linkUID in incomingLinks + outgoingLinks]

        descriptionLabel = QtWidgets.QLabel("Use the '+' and '-' buttons to create and remove entities. For each "
                                            "resolution column in each entity row, set the checkbox to selected "
                                            "if you want the corresponding entity to have the resolution on the "
                                            "selected column.")
        descriptionLabel.setWordWrap(True)

        dialogLayout = QtWidgets.QGridLayout()
        self.setLayout(dialogLayout)
        self.entitiesTable = QtWidgets.QTableWidget(0, len(self.allLinks) + 1, self)
        # Resize columns to give a bit more space to each column.
        for columnIndex in range(self.entitiesTable.columnCount()):
            self.entitiesTable.setColumnWidth(columnIndex, 150)

        horizontalHeaderLabels = []
        for incomingLink in incomingLinks:
            linkNode = parent.LENTDB.getEntity(incomingLink[0])
            linkNodeName = linkNode[list(linkNode)[1]]
            horizontalHeaderLabels.append('Incoming From:\n' + linkNodeName)

        for outgoingLink in outgoingLinks:
            linkNode = parent.LENTDB.getEntity(outgoingLink[1])
            linkNodeName = linkNode[list(linkNode)[1]]
            horizontalHeaderLabels.append('Outgoing To:\n' + linkNodeName)

        self.entitiesTable.setHorizontalHeaderLabels(['Entity Name:'] + horizontalHeaderLabels)

        self.insertRow(self.entityToSplitPrimaryField)

        self.entitiesTable.setMinimumWidth(self.entitiesTable.width())

        self.addSplitEntity = QtWidgets.QPushButton('+')
        self.addSplitEntity.clicked.connect(self.insertRow)
        self.removeSplitEntity = QtWidgets.QPushButton('-')
        self.removeSplitEntity.clicked.connect(self.removeRow)

        dialogLayout.addWidget(descriptionLabel, 0, 0, 2, 4)
        dialogLayout.addWidget(self.entitiesTable, 2, 1, 4, 3)
        dialogLayout.addWidget(self.addSplitEntity, 2, 0, 1, 1)
        dialogLayout.addWidget(self.removeSplitEntity, 3, 0, 1, 1)
        dialogLayout.setRowStretch(4, 1)
        dialogLayout.setColumnStretch(1, 1)
        dialogLayout.setColumnStretch(2, 1)
        dialogLayout.setColumnStretch(3, 1)

        acceptButton = QtWidgets.QPushButton('Accept')
        cancelButton = QtWidgets.QPushButton('Cancel')
        acceptButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)
        dialogLayout.addWidget(cancelButton, 6, 0, 1, 2)
        dialogLayout.addWidget(acceptButton, 6, 2, 1, 2)

        self.adjustSize()
        self.setMaximumHeight(700)
        self.setMinimumWidth(min(self.entitiesTable.width(), 700))

    def insertRow(self, entityPrimaryField: str = '') -> None:
        # Do not allow splitting into more than 5 entities at a time for performance reasons.
        if self.entitiesTable.rowCount() == 5:
            self.parent.MESSAGEHANDLER.info('Maximum number of entities to split into reached.')
            return
        newRowIndex = self.entitiesTable.rowCount()
        self.entitiesTable.insertRow(newRowIndex)

        self.entitiesTable.setItem(newRowIndex, 0, QtWidgets.QTableWidgetItem(entityPrimaryField))
        self.entitiesTable.setFocus()

        count = 1
        for link in self.allLinks:
            selectResolution = QtWidgets.QCheckBox(link['Resolution'])
            selectResolution.setStyleSheet(Stylesheets.CHECK_BOX_STYLESHEET)
            selectResolution.linkUID = link['uid']
            self.entitiesTable.setCellWidget(newRowIndex, count, selectResolution)
            count += 1

    def removeRow(self) -> None:
        self.entitiesTable.removeRow(self.entitiesTable.rowCount() - 1)

    def accept(self) -> None:
        for newEntityRow in range(self.entitiesTable.rowCount()):
            entityName = self.entitiesTable.item(newEntityRow, 0).text()
            if entityName == '':
                self.parent.MESSAGEHANDLER.info('Cannot split into entities with blank primary fields.',
                                                popUp=True)
                self.splitEntities = []
                self.splitEntitiesWithLinks = []
                return
            elif self.parent.LENTDB.doesEntityExist(entityName) and entityName != self.entityToSplitPrimaryField:
                self.parent.MESSAGEHANDLER.info("Entity primary field value specified already exists:\n" + entityName,
                                                popUp=True)
                self.splitEntities = []
                self.splitEntitiesWithLinks = []
                return
            elif entityName in self.splitEntities:
                self.parent.MESSAGEHANDLER.info("Duplicate primary field value specified:\n" + entityName,
                                                popUp=True)
                self.splitEntities = []
                self.splitEntitiesWithLinks = []
                return
            self.splitEntities.append(entityName)

            allLinkUIDsForEntity = []
            for columnIndex in range(1, self.entitiesTable.columnCount()):
                if self.entitiesTable.cellWidget(newEntityRow, columnIndex).isChecked():
                    allLinkUIDsForEntity.append(self.allLinks[columnIndex - 1])
            self.splitEntitiesWithLinks.append((entityName, allLinkUIDsForEntity))

        # Clear out this list, no more need for it
        self.splitEntities = []
        super(SplitEntitiesDialog, self).accept()


if __name__ == '__main__':
    # Create a graphical application
    application = QtWidgets.QApplication(sys.argv)
    mainWindow = MainWindow()
    sys.exit(application.exec())
