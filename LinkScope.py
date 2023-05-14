#!/usr/bin/env python3

# Load modules
import contextlib
import re
import sys
import tempfile
import time
import csv
import statistics
import itertools
import threading

import networkx as nx
import qdarktheme
from shutil import rmtree
from svglib.svglib import svg2rlg
from ast import literal_eval
from uuid import uuid4
from shutil import move
from inspect import getsourcefile
from os import listdir, access, R_OK, W_OK, getpid, kill
from os.path import abspath, dirname
from msgpack import load
from pathlib import Path
from datetime import datetime
from typing import Union, Any
from PySide6 import QtWidgets, QtGui, QtCore, QtCharts

from Core import MessageHandler, SettingsObject
from Core import ResourceHandler
from Core import ModuleManager
from Core import ReportGeneration
from Core import EntityDB
from Core import ResolutionManager
from Core import URLManager
from Core import FrontendCommunicationsHandler
from Core.ResourceHandler import StringPropertyInput, FilePropertyInput, SingleChoicePropertyInput, \
    MultiChoicePropertyInput
from Core.Interface import CentralPane
from Core.Interface import DockBarOne, DockBarTwo, DockBarThree
from Core.Interface import ToolBarOne
from Core.Interface import MenuBar
from Core.Interface.Entity import BaseNode, BaseConnector, GroupNode
from Core.LQL import LQLQueryBuilder
from Core.PathHelper import is_path_exists_or_creatable_portable


# Main Window of Application
class MainWindow(QtWidgets.QMainWindow):
    facilitateResolutionSignalListener = QtCore.Signal(str, list)
    notifyUserSignalListener = QtCore.Signal(str, str, bool)
    statusBarSignalListener = QtCore.Signal(str)
    warningSignalListener = QtCore.Signal(str, bool)
    runningMacroResolutionFinishedSignalListener = QtCore.Signal(str, str, list)

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
        if not newChildren:
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
        self.SETTINGS.setGlobalValue("MainWindow/Geometry", self.saveGeometry().data())
        self.SETTINGS.setGlobalValue("MainWindow/WindowState", self.saveState().data())
        self.SETTINGS.setGlobalValue("Program/Usage/First Time Start", False)
        if self.FCOM.isConnected():
            self.FCOM.close()
        self.SETTINGS.setValue("Project/Server/Project", "")
        self.saveProject()
        # Wait just a little for the logging thread to close.
        # We don't _have_ to do this, but it stops errors from popping up due to threads being rudely interrupted.
        while not self.dockbarThree.logViewerUpdateThread.isFinished():
            time.sleep(0.01)
        super(MainWindow, self).closeEvent(event)
        # Terminating ThreadPoolExecutor threads, so that the application quits.
        for thread in threading.enumerate():
            if 'ThreadPoolExecutor' in thread.name:
                # Yes, this is terrible. Whenever ThreadPoolExecutor allows for the creation of actual daemon threads
                #   that don't cause the program to hang, this will be removed.
                kill(getpid(), 9)

    def saveHelper(self) -> None:
        """
        This is where all the saving is done.
        Add all save methods here.

        NOTE: This function should only be called inside a try/catch.
        @return:
        """
        self.LENTDB.save()
        self.RESOLUTIONMANAGER.save()
        self.MODULEMANAGER.save()
        self.SETTINGS.save()
        self.centralWidget().tabbedPane.save()

    def resetMainWindowTitle(self):
        self.setWindowTitle(f"LinkScope {self.SETTINGS.value('Program/Version', 'N/A')}"
                            f" - {self.SETTINGS.value('Project/Name', 'Untitled')}")

    def saveProject(self) -> None:
        try:
            self.saveHelper()
            self.setStatus("Project Saved.", 3000)
            self.MESSAGEHANDLER.info('Project Saved')
        except Exception as e:
            errorMessage = f"Could not Save Project: {repr(e)}"
            self.MESSAGEHANDLER.error(errorMessage, exc_info=True)
            self.setStatus("Failed Saving Project.", 3000)
            self.MESSAGEHANDLER.info("Failed Saving Project " + self.SETTINGS.value("Project/Name", 'Untitled'))

    def autoSaveProject(self):
        try:
            self.saveHelper()
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
        saveAsDialog.setOption(QtWidgets.QFileDialog.Option.DontUseNativeDialog, True)
        saveAsDialog.setViewMode(QtWidgets.QFileDialog.ViewMode.List)
        saveAsDialog.setFileMode(QtWidgets.QFileDialog.FileMode.AnyFile)
        saveAsDialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        saveAsDialog.setDirectory(str(Path.home()))

        if not saveAsDialog.exec():
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
            self.MESSAGEHANDLER.error('Cannot save project into a non-existing parent directory. '
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
            self.MESSAGEHANDLER.error('Cannot save project into a non-existing parent directory. '
                                      'Please create the required parent directories and try again.',
                                      popUp=True, exc_info=False)
            self.SETTINGS.setValue("Project/BaseDir", oldBaseDir)
            self.SETTINGS.setValue("Project/FilesDir", oldFilesDir)
            self.SETTINGS.setValue("Project/Name", oldName)
            return

        self.resetMainWindowTitle()
        self.saveProject()
        self.setStatus(f'Project Saved As: {newProjectPath.name}')

    # https://networkx.org/documentation/stable/reference/readwrite/graphml.html
    def exportCanvasToGraphML(self):
        currentCanvasGraph = self.centralWidget().tabbedPane.getCurrentScene().sceneGraph
        saveAsDialog = QtWidgets.QFileDialog()
        saveAsDialog.setOption(QtWidgets.QFileDialog.Option.DontUseNativeDialog, True)
        saveAsDialog.setViewMode(QtWidgets.QFileDialog.ViewMode.List)
        saveAsDialog.setNameFilter("GraphML (*.xml)")
        saveAsDialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        saveAsDialog.setDirectory(str(Path.home()))

        if saveAsDialog.exec():
            try:
                filePath = saveAsDialog.selectedFiles()[0]
                if Path(filePath).suffix != '.xml':
                    filePath += '.xml'
                nx.write_graphml(currentCanvasGraph, filePath)
                self.setStatus('Canvas exported successfully.')
            except Exception as exc:
                self.MESSAGEHANDLER.error(f"Could not export canvas to file: {str(exc)}", popUp=True)
                self.setStatus('Canvas export failed.')

    def importCanvasFromGraphML(self):
        openDialog = QtWidgets.QFileDialog()
        openDialog.setOption(QtWidgets.QFileDialog.Option.DontUseNativeDialog, True)
        openDialog.setViewMode(QtWidgets.QFileDialog.ViewMode.List)
        openDialog.setNameFilter("GraphML (*.xml)")
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
                    # Create new group entity, so we don't mess with the contents of the original.
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
                self.MESSAGEHANDLER.error(f"Cannot import canvas: {str(exc)}", popUp=True)
                self.setStatus('Canvas import failed.')

    def exportDatabaseToGraphML(self):
        # Need to create a new database to remove the icons
        with self.LENTDB.dbLock:
            currentDatabase = self.LENTDB.database.copy()

        for node in currentDatabase.nodes:
            # Remove icons. Will reset custom icons to default, but saves space.
            del currentDatabase.nodes[node]['Icon']
            if currentDatabase.nodes[node].get('Child UIDs'):
                currentDatabase.nodes[node]['Child UIDs'] = str(currentDatabase.nodes[node]['Child UIDs'])

        for edge in currentDatabase.edges:
            currentDatabase.edges[edge]['uid'] = str(currentDatabase.edges[edge]['uid'])

        saveAsDialog = QtWidgets.QFileDialog()
        saveAsDialog.setOption(QtWidgets.QFileDialog.Option.DontUseNativeDialog, True)
        saveAsDialog.setViewMode(QtWidgets.QFileDialog.ViewMode.List)
        saveAsDialog.setNameFilter("GraphML (*.xml)")
        saveAsDialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        saveAsDialog.setDirectory(str(Path.home()))

        if saveAsDialog.exec():
            try:
                filePath = saveAsDialog.selectedFiles()[0]
                if Path(filePath).suffix != '.xml':
                    filePath += '.xml'
                nx.write_graphml(currentDatabase, filePath)
                self.setStatus('Database exported successfully.')
            except Exception as exc:
                self.MESSAGEHANDLER.error(f"Could not export database to file: {str(exc)}", popUp=True)
                self.setStatus('Database export failed.')

    def importDatabaseFromGraphML(self):
        openDialog = QtWidgets.QFileDialog()
        openDialog.setOption(QtWidgets.QFileDialog.Option.DontUseNativeDialog, True)
        openDialog.setViewMode(QtWidgets.QFileDialog.ViewMode.List)
        openDialog.setNameFilter("GraphML (*.xml)")
        openDialog.setDirectory(str(Path.home()))

        if openDialog.exec():
            try:
                filePath = openDialog.selectedFiles()[0]
                read_graphml = nx.read_graphml(filePath)
                read_graphml_nodes = {key: read_graphml.nodes[key] for key in read_graphml.nodes}
                read_graphml_edges = {key: read_graphml.edges[key] for key in read_graphml.edges}
                for nodeValue in read_graphml_nodes.values():
                    # Make sure that all the necessary values are assigned.
                    # This will throw an exception if the user imports an entity without a type.
                    nodeValue = self.RESOURCEHANDLER.getEntityJson(nodeValue['Entity Type'], nodeValue)
                    if nodeValue.get('Child UIDs'):
                        nodeValue['Child UIDs'] = literal_eval(nodeValue['Child UIDs'])
                for edge in read_graphml_edges:
                    read_graphml_edges[edge]['uid'] = literal_eval(read_graphml_edges[edge]['uid'])
                    # Make sure that all the necessary values are assigned.
                    read_graphml_edges[edge] = self.RESOURCEHANDLER.getLinkJson(read_graphml_edges[edge])
                self.LENTDB.mergeDatabases(read_graphml_nodes, read_graphml_edges, fromServer=False)
                self.dockbarOne.existingEntitiesPalette.loadEntities()
                self.LENTDB.resetTimeline()
                self.setStatus('Database imported successfully.')
            except Exception as exc:
                self.MESSAGEHANDLER.error(f"Could not import database from file: {str(exc)}", popUp=True)
                self.setStatus('Database import failed.')

    def generateReport(self):
        wizard = ReportWizard(self)
        wizard.show()

    def renameProjectPromptName(self) -> None:
        newName, confirm = QtWidgets.QInputDialog.getText(self,
                                                          'Rename Project',
                                                          'New Name:',
                                                          QtWidgets.QLineEdit.EchoMode.Normal,
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
        oldProjectFile = newBaseDir.joinpath(f'{oldName}.linkscope')
        oldProjectFile.unlink(missing_ok=True)

        self.resetMainWindowTitle()
        self.saveProject()
        statusMessage = f'Project Renamed to: {newName}'
        self.setStatus(statusMessage)
        self.MESSAGEHANDLER.info(statusMessage)

    def addCanvas(self) -> None:
        # Create or open canvas
        connected = self.FCOM.isConnected()
        with self.syncedCanvasesLock:
            availableSyncedCanvases = self.syncedCanvases
        newCanvasPopup = CreateOrOpenCanvas(self, connected, availableSyncedCanvases)
        if newCanvasPopup.exec():
            self.MESSAGEHANDLER.info(f"New Canvas added: {newCanvasPopup.canvasName}")

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
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            self.linkingNodes = False
        else:
            self.centralWidget().tabbedPane.disableAllTabsExceptCurrent()
            currentScene.linking = True
            currentScene.itemsToLink = []
            currentScene.clearSelection()
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.CrossCursor))
            self.linkingNodes = True

    def deleteSpecificEntity(self, itemUID: str) -> None:
        self.centralWidget().tabbedPane.nodeRemoveAllHelper(itemUID)
        self.LENTDB.removeEntity(itemUID)
        self.MESSAGEHANDLER.info(f"Deleted node: {itemUID}")

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
            self.MESSAGEHANDLER.info(f"Deleted link: {str(linkUID)}")

    def setGroupAppendMode(self, enable: bool) -> None:
        if self.centralWidget().tabbedPane.getCurrentScene().linking:
            message = 'Cannot append to group: Currently creating new link.'
            self.setStatus(message)
            self.MESSAGEHANDLER.info(message, popUp=True)
            return
        if enable:
            self.centralWidget().tabbedPane.disableAllTabsExceptCurrent()
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        else:
            self.centralWidget().tabbedPane.enableAllTabs()
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))

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
        currentScene = self.centralWidget().tabbedPane.getCurrentScene()
        currentScene.clearSelection()
        for isolatedNodeUID in nx.isolates(currentScene.sceneGraph):
            currentScene.nodesDict[isolatedNodeUID].setSelected(True)

    def selectNonIsolatedNodes(self) -> None:
        """
        Select all nodes with at least one link going into or out of them.
        :return:
        """
        currentScene = self.centralWidget().tabbedPane.getCurrentScene()
        currentScene.clearSelection()
        isolatedNodes = list(nx.isolates(currentScene.sceneGraph))
        for node in currentScene.nodesDict:
            if node not in isolatedNodes:
                currentScene.nodesDict[node].setSelected(True)

    def findShortestPath(self) -> None:
        """
        Find the shortest path between two nodes, if it exists.
        Exactly two nodes must be selected.
        :return:
        """
        currentScene = self.centralWidget().tabbedPane.getCurrentScene()
        endPoints = [item.uid for item in currentScene.selectedItems()
                     if isinstance(item, BaseNode)]
        if len(endPoints) != 2:
            self.MESSAGEHANDLER.warning('Exactly two entities must be selected for the Shortest Path function to work.',
                                        popUp=True)
            return
        currentCanvasGraph = currentScene.sceneGraph
        try:
            shortestPath = nx.shortest_path(currentCanvasGraph, endPoints[0], endPoints[1])
        except nx.NetworkXNoPath:
            try:
                shortestPath = nx.shortest_path(currentCanvasGraph, endPoints[1], endPoints[0])
            except nx.NetworkXNoPath:
                shortestPath = None

        if shortestPath is None:
            messagePathNotFound = f'No path found connecting the selected nodes: {endPoints}'
            self.setStatus(messagePathNotFound)
            self.MESSAGEHANDLER.info(messagePathNotFound, popUp=True)
        else:
            currentScene.clearSelection()

            for itemUID in currentScene.nodesDict:
                if itemUID in shortestPath:
                    currentScene.nodesDict[itemUID].setSelected(True)

            linksToSelect = list(zip(shortestPath, shortestPath[1:]))
            for linkItem in [link for link in currentScene.items() if isinstance(link, BaseConnector)]:
                if linkItem.uid.intersection(linksToSelect):
                    linkItem.setSelected(True)
            self.setStatus('Shortest path found.')

    def extractCycles(self) -> None:
        """
        Find cycles in the graph, optionally involving selected nodes.
        :return:
        """
        currentScene = self.centralWidget().tabbedPane.getCurrentScene()
        canvasName = currentScene.getSelfName()
        endPoints = [item.uid for item in currentScene.selectedItems()
                     if isinstance(item, BaseNode)]
        currentCanvasGraph = currentScene.sceneGraph
        tempGraph = currentCanvasGraph.copy()
        # Just in case.
        tempGraph.remove_edges_from(nx.selfloop_edges(currentCanvasGraph))

        newCyclesThread = ExtractCyclesThread(tempGraph, endPoints, canvasName)
        newCyclesThread.cyclesSignal.connect(self.extractCyclesResultHandler)
        self.MESSAGEHANDLER.info(f'Extracting Cycles from Canvas: {canvasName}')
        newCyclesThread.start()
        self.cycleExtractionThreads.append(newCyclesThread)

    def extractCyclesResultHandler(self, results: list, canvasName: str) -> None:
        if not results:
            self.MESSAGEHANDLER.info(f'No Cycles in Canvas: {canvasName}')
        else:
            count = 0
            while True:
                newCanvasName = f'{canvasName} Cycles #{str(count)}'
                if self.centralWidget().tabbedPane.addCanvas(newCanvasName):
                    break
                else:
                    count += 1

            nodesToAdd = results[0]
            groupsToMake = results[1]
            newCanvas = self.centralWidget().tabbedPane.canvasTabs[newCanvasName].scene()

            for node in nodesToAdd:
                newCanvas.addNodeProgrammatic(node)

            entitiesAlreadyInGroups = set()
            for count, group in enumerate(groupsToMake, start=1):
                newGroup = set()
                for groupEntity in group:
                    if groupEntity not in entitiesAlreadyInGroups:
                        newGroup.add(groupEntity)
                        entitiesAlreadyInGroups.add(groupEntity)
                newCanvas.groupItemsProgrammatic(newGroup, f'Group {str(count)}')
            newCanvas.rearrangeGraph('circular')

        for cycleThread in list(self.cycleExtractionThreads):
            if cycleThread.isFinished():
                cycleThread.deleteLater()
                self.cycleExtractionThreads.remove(cycleThread)

    def findEntityOrLinkOnCanvas(self, regex: bool = False) -> None:
        currentScene = self.centralWidget().tabbedPane.getCurrentScene()
        currentUIDs = [item.uid for item in currentScene.items() if isinstance(item, (BaseNode, BaseConnector))]
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
            findText = findPrompt.findInput.text()
            if findText != "":
                uidsToSelect = []
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
                                 if isinstance(linkOrEntity, (BaseNode, BaseConnector))]:
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

        findPrompt = FindEntityOfTypeOnCanvasDialog(self, entityTypesOnCanvas, regex)

        if findPrompt.exec():
            findText = findPrompt.findInput.text()
            findType = findPrompt.typeInput.currentText()
            if findText != "":
                uidsToSelect = []
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
        if not validEntityToSplit:
            self.MESSAGEHANDLER.info('No valid entities to split selected! Please choose at least one non-Meta entity.',
                                     popUp=True)
            return
        elif len(validEntityToSplit) > 1:
            self.MESSAGEHANDLER.info('Multiple entities selected. Please pick one valid entity to split.',
                                     popUp=True)
            return

        # Continue only if a single entity is selected.
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
                    if field not in ['uid', entityToSplitPrimaryFieldKey]:
                        newEntity[field] = entityToSplit[field]
                newEntity = self.LENTDB.addEntity(newEntity)

                for link in newEntityWithLinks[1]:
                    newLink = {field: link[field] for field in link}
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

    def launchQueryWizard(self):
        queryWizard = QueryBuilderWizard(self)
        queryWizard.exec()

    def handleGroupNodeUpdateAfterEntityDeletion(self, entityUID) -> None:
        for canvas in self.centralWidget().tabbedPane.canvasTabs:
            self.centralWidget().tabbedPane.canvasTabs[canvas].cleanDeletedNodeFromGroupsIfExists(entityUID)

    def editProjectSettings(self) -> None:
        settingsDialog = ProjectEditDialog(self.SETTINGS)
        if settingsDialog.exec():
            # Save new settings
            newSettings = settingsDialog.newSettings
            for key in newSettings:
                newSettingValue = newSettings[key]
                if newSettingValue[1]:
                    # Delete key
                    self.SETTINGS.removeKey(key)
                elif newSettingValue[0] != '':
                    # Do not allow blank settings.
                    if key in ['Project/Resolution Result Grouping Threshold', 'Project/Number of Answers Returned',
                               'Project/Question Answering Retriever Value', 'Project/Question Answering Reader Value']:
                        with contextlib.suppress(ValueError):
                            int(newSettingValue[1])
                            self.SETTINGS.setValue(key, newSettingValue[0])
                    elif newSettingValue[0] in ['Copy', 'Symlink']:
                        self.SETTINGS.setValue(key, newSettingValue[0])

            self.saveProject()

    def editResolutionsSettings(self) -> None:
        settingsDialog = ResolutionsEditDialog(self.SETTINGS)
        if settingsDialog.exec():
            # Save new settings
            newSettings = settingsDialog.newSettings
            for key in newSettings:
                newSettingValue = newSettings[key]
                if newSettingValue[1]:
                    # Delete key
                    self.SETTINGS.removeKey(key)
                elif newSettingValue[0] != '':
                    # Do not allow blank settings.
                    self.SETTINGS.setValue(key, newSettingValue[0])

            self.saveProject()

    def editLogSettings(self) -> None:
        settingsDialog = LoggingSettingsDialog(self.SETTINGS)
        if settingsDialog.exec():
            # Save new settings
            newSettings = settingsDialog.newSettings
            for key in newSettings:
                newSettingValue = newSettings[key]
                if newSettingValue[1]:
                    # Delete key
                    self.SETTINGS.removeKey(key)
                elif newSettingValue[0] != '':
                    # Do not allow blank settings.
                    self.SETTINGS.setValue(key, newSettingValue[0])

            self.MESSAGEHANDLER.setSeverityLevel(self.SETTINGS.value('Logging/Severity'))
            self.MESSAGEHANDLER.changeLogfile(self.SETTINGS.value('Logging/Logfile'))
            self.saveProject()

    def editProgramSettings(self) -> None:
        settingsDialog = ProgramEditDialog(self)
        if settingsDialog.exec():
            # Save new settings
            newSettings = settingsDialog.newSettings
            for key in newSettings:
                newSettingValue = newSettings[key]
                if newSettingValue[1]:
                    # Delete key
                    self.SETTINGS.removeKey(key)
                elif newSettingValue[0] != '':
                    # Do not allow blank settings.
                    self.SETTINGS.setValue(key, newSettingValue[0])

            self.saveProject()

    def changeGraphics(self) -> None:
        settingsDialog = GraphicsEditDialog(self.SETTINGS, self.RESOURCEHANDLER)

        if settingsDialog.exec():
            newSettings = settingsDialog.newSettings
            with contextlib.suppress(ValueError):
                etfVal = int(newSettings["ETF"])
                self.centralWidget().tabbedPane.entityTextFont.setPointSize(etfVal)
                self.SETTINGS.setGlobalValue("Program/Graphics/Entity Text Font Size", str(newSettings["ETF"]))
            with contextlib.suppress(ValueError):
                ltfVal = int(newSettings["LTF"])
                self.centralWidget().tabbedPane.linkTextFont.setPointSize(ltfVal)
                self.SETTINGS.setGlobalValue("Program/Graphics/Link Text Font Size", str(newSettings["LTF"]))
            with contextlib.suppress(ValueError):
                lfVal = int(newSettings["LF"])
                self.centralWidget().tabbedPane.hideZoom = -lfVal
                self.centralWidget().tabbedPane.updateCanvasHideZoom()
                self.SETTINGS.setGlobalValue("Program/Graphics/Label Fade Scroll Distance", str(newSettings["LF"]))
            etcVal = newSettings["ETC"]
            newEtcColor = QtGui.QColor(etcVal)
            if newEtcColor.isValid():
                self.centralWidget().tabbedPane.entityTextBrush.setColor(newEtcColor)
                self.SETTINGS.setGlobalValue("Program/Graphics/Entity Text Color", newEtcColor.name())
            ltcVal = newSettings["LTC"]
            newLtcColor = QtGui.QColor(ltcVal)
            if newLtcColor.isValid():
                self.centralWidget().tabbedPane.linkTextBrush.setColor(newLtcColor)
                self.SETTINGS.setGlobalValue("Program/Graphics/Link Text Color", newLtcColor.name())

            self.centralWidget().tabbedPane.updateCanvasGraphics()
            self.saveProject()

    def loadModules(self) -> None:
        """
        Loads user-defined modules from the Modules folder in the installation directory.
        :return:
        """
        self.MODULEMANAGER.loadAllModules()
        self.setStatus('Loaded Modules.')

    def reloadModules(self) -> None:
        """
        Same as loadModules, except this one updates the GUI to show newly loaded entities and resolutions.
        This is meant to be run after the application started, in case the user wants to load a module without
        closing and reopening the application.
        :return:
        """
        self.MODULEMANAGER.loadAllModules()
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
                eJson.extend(self.LENTDB.getLink(linkUID) for linkUID in uid)
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
            with contextlib.suppress(KeyError):
                scene.nodesDict[uid].updateLabel(label)

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
            with contextlib.suppress(KeyError):
                scene.linksDict[uid].updateLabel(label)

    def populateEntitiesWidget(self, eJson: dict, add: bool) -> None:
        if add:
            self.dockbarOne.existingEntitiesPalette.addEntity(eJson)
        else:
            self.dockbarOne.existingEntitiesPalette.removeEntity(eJson)

    def populateResolutionsWidget(self, selected) -> None:
        self.dockbarOne.resolutionsPalette.loadResolutionsForSelected(selected)

    def popParameterValuesAndReturnSpecified(self, resolutionName: str, parameters: dict,
                                             preSpecifiedParameters: dict = None) -> dict:
        """
        This takes a dict of parameters (see Example Resolution for dict format) and a resolution name.
        We remove the specified parameters from the given 'parameters' dict, and return a dict with
          their respective values.

        @param preSpecifiedParameters: Optional dict containing values provided via alternative means (i.e. macros)
        @param resolutionName: The name of the resolution whose parameters we are getting
        @param parameters: The parameter dict of a resolution
        @return:
        """
        specifiedParameterValues = {}
        # New dict given in argument, so we can pop stuff from it while we loop through it.
        for parameter in dict(parameters):
            if preSpecifiedParameters is not None and parameter in preSpecifiedParameters:
                savedParameterValue = preSpecifiedParameters.get(parameter)
            elif parameters[parameter].get('global') is True:
                # Extra slash in the middle to ensure that resolutions cannot overwrite these accidentally (or not),
                #   since slashes are not allowed by default on Linux or Windows.
                savedParameterValue = self.SETTINGS.value(f'Resolutions/Global/Parameters/{parameter}')
            else:
                savedParameterValue = self.SETTINGS.value(f'Resolutions/{resolutionName}/{parameter}')
            if savedParameterValue is not None:
                specifiedParameterValues[parameter] = savedParameterValue
                parameters.pop(parameter)
        return specifiedParameterValues

    def runResolution(self, resolutionName, preSpecifiedUID: str = None, preSpecifiedEntities: list = None,
                      preSpecifiedParameters: dict = None) -> str:
        """
        Runs the specified resolution in another thread.
        """
        try:
            category, resolution = resolutionName.split('/', 1)
        except ValueError:
            self.MESSAGEHANDLER.error(
                f'Category name or resolution name should not contain slashes: {resolutionName}'
            )
            return ""

        if preSpecifiedEntities:
            resolutionInputEntities = preSpecifiedEntities
        else:
            scene = self.centralWidget().tabbedPane.getCurrentScene()
            items = scene.selectedItems()
            resolutionInputEntities = [self.LENTDB.getEntity(item.uid) for item in items if isinstance(item, BaseNode)]

        parameters = self.RESOLUTIONMANAGER.getResolutionParameters(category, resolution)
        if parameters is None:
            message = f'Resolution parameters not found for resolution: {resolution}'
            self.MESSAGEHANDLER.error(message, popUp=True, exc_info=False)
            self.setStatus(message)
            return ""

        resolutionParameterValues = self.popParameterValuesAndReturnSpecified(resolution, parameters,
                                                                              preSpecifiedParameters)
        # Show Resolution wizard if there are any parameters required that aren't saved in settings, or
        #   if the user did not select any items to run the resolution on.
        # Note that at this point, the parameters dict contains only the parameters that are unspecified, i.e.
        #   ones that were not saved previously.
        if not resolutionInputEntities or parameters:
            selectEntityList = None
            uidAndPrimaryFields: list = []
            acceptableOriginTypes = None
            resolutionDescription = None
            if not resolutionInputEntities:
                acceptableOriginTypes = self.RESOLUTIONMANAGER.getResolutionOriginTypes(resolutionName)
                uidAndPrimaryFields = [(entity['uid'], entity[list(entity)[1]])
                                       for entity in self.LENTDB.getAllEntities()
                                       if entity['Entity Type'] in acceptableOriginTypes]
                selectEntityList = [entity[1] for entity in uidAndPrimaryFields]
                resolutionDescription = self.RESOLUTIONMANAGER.getResolutionDescription(resolutionName)

            parameterSelector = ResolutionParametersSelector(self, resolution, parameters,
                                                             selectEntityList, acceptableOriginTypes,
                                                             resolutionDescription)
            if parameterSelector.exec():
                resolutionParameterValues.update(parameterSelector.chosenParameters)

                if not resolutionInputEntities:
                    selectedEntities = parameterSelector.entitySelector.selectedItems()
                    if len(selectedEntities) == 0:
                        self.setStatus(f'Resolution {resolution} did not run: No entities selected.')
                        return ""

                    for selectedEntity in selectedEntities:
                        uid = uidAndPrimaryFields[selectEntityList.index(selectedEntity.text())][0]
                        resolutionInputEntities.append(self.LENTDB.getEntity(uid))

            else:
                self.setStatus(f'Resolution {resolution} aborted.')
                return ""
        resolutionParameterValues['Project Files Directory'] = self.SETTINGS.value("Project/FilesDir")
        resolutionUID = preSpecifiedUID or str(uuid4())
        resolutionThread = ResolutionExecutorThread(
            resolutionName, resolutionInputEntities, resolutionParameterValues, self, resolutionUID)
        resolutionThread.sig.connect(self.resolutionSignalListener)
        resolutionThread.sigStr.connect(self.resolutionSignalListener)
        resolutionThread.sigError.connect(self.resolutionErrorSignalListener)
        self.MESSAGEHANDLER.info(f'Running Resolution: {resolution}')
        self.setStatus(f"Running Resolution: {resolution}")
        resolutionThread.start()
        self.resolutions.append((resolutionThread, category == 'Server Resolutions'))
        return resolutionUID

    def resolutionSignalListener(self, resolution_name: str, resolution_result: Union[list, str],
                                 resolution_uid: str) -> None:
        """
        Is called by the threads created by runResolution to handle the
        result, i.e. run the function that adds nodes and links.
        """
        affectedUIDs = []
        if isinstance(resolution_result, str):
            self.MESSAGEHANDLER.info(f"Resolution {resolution_name} finished with status: {resolution_result}",
                                     popUp=True)
        elif len(resolution_result) == 0:
            self.MESSAGEHANDLER.info(f"Resolution {resolution_name} returned no results.", popUp=True)
        else:
            affectedUIDs = self.centralWidget().tabbedPane.facilitateResolution(resolution_name, resolution_result)

        self.cleanUpLocalFinishedResolutions()
        self.setStatus(f"Resolution: {resolution_name} completed.")
        self.runningMacroResolutionFinishedSignalListener.emit(resolution_name, resolution_uid, affectedUIDs)

    def resolutionErrorSignalListener(self, error_message: str):
        self.MESSAGEHANDLER.error(error_message, popUp=True)

    def cleanUpLocalFinishedResolutions(self) -> None:
        """
        Clean out old non-server resolutions.
        :return:
        """
        for resolutionThread in list(self.resolutions):
            if resolutionThread[0].isFinished() and resolutionThread[1] is False:
                resolutionThread[0].deleteLater()
                self.resolutions.remove(resolutionThread)

    def resolutionFinishedMacrosListener(self, resolution_name: str, resolution_uid: str,
                                         affectedEntityUIDs: list) -> None:
        """
        When user runs macro, the macro goes into a list.
        Emissions from resolutionSignalListener are caught here, and the macro keeps track of what
          UIDs correspond to each stage of itself, and progresses appropriately.
        @param affectedEntityUIDs:
        @param resolution_name:
        @param resolution_uid:
        @return:
        """
        with self.macrosLock:
            macroValid = False
            for runningMacro in self.runningMacros:
                currentResolutionForMacro = runningMacro[0]
                if resolution_name == currentResolutionForMacro[0] and \
                        resolution_uid == currentResolutionForMacro[1]:
                    macroValid = True
                    break

            if macroValid:
                runNext = False
                runningMacro.pop(0)
                if runningMacro:
                    nextResolutionForMacro = runningMacro[0]

                    acceptableOriginTypes = self.RESOLUTIONMANAGER.getResolutionOriginTypes(nextResolutionForMacro[0])
                    fullEntityJsonList = [self.LENTDB.getEntity(entityUID) for entityUID in set(affectedEntityUIDs)]
                    if filteredEntityJsonList := [
                        entity
                        for entity in fullEntityJsonList
                        if entity['Entity Type'] in acceptableOriginTypes
                    ]:
                        preparedResolutionArguments = [nextResolutionForMacro[0], nextResolutionForMacro[1],
                                                       filteredEntityJsonList, nextResolutionForMacro[2]]
                        runNext = True
                if not runNext:
                    self.setStatus('Macro execution finished.')
                    self.runningMacros.remove(runningMacro)
        if macroValid and runNext:
            self.runResolution(*preparedResolutionArguments)

    def showMacrosDialog(self) -> None:
        """
        Also runs any macros selected by the user.
        @return:
        """
        macrosDialog = MacroDialog(self)
        if macrosDialog.exec():
            macrosToRun = []
            macroTreeRoot = macrosDialog.macroTree.invisibleRootItem()
            for itemIndex in range(macroTreeRoot.childCount()):
                item = macroTreeRoot.child(itemIndex)
                if item.isSelected():
                    macrosToRun.append(item.text(0))
            if macrosToRun:
                currentScene = self.centralWidget().tabbedPane.getCurrentScene()
                selectedNodes = [self.LENTDB.getEntity(item.uid) for item in currentScene.selectedItems()
                                 if isinstance(item, BaseNode)]
                for macro in macrosToRun:
                    self.runMacro(macro, selectedNodes)

    def runMacro(self, uid: str, selectedEntities: list) -> None:
        macroDetails = self.RESOLUTIONMANAGER.macros[uid]
        macroStructure = []
        try:
            with self.macrosLock:
                for resolutionElement in macroDetails:
                    newResolutionUID = str(uuid4())
                    macroStructure.append((resolutionElement[0], newResolutionUID, resolutionElement[1]))
                self.runningMacros.append(macroStructure)
            firstResolutionDetails = macroStructure[0]
            runResResult = self.runResolution(firstResolutionDetails[0], firstResolutionDetails[1], selectedEntities,
                                              firstResolutionDetails[2])
            if runResResult != "":
                self.MESSAGEHANDLER.info(f'Running Macro: {uid}')
            else:
                self.setStatus("Did not run Macro.")
        except Exception as e:
            message = f"Failed to run Macro. Reason: {str(e)}"
            self.MESSAGEHANDLER.error(message, popUp=True, exc_info=False)
            self.setStatus(message)

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
                self.MESSAGEHANDLER.debug(f'Cannot eval Project/Server/Collectors setting: {str(e)}')
                clientCollectorUIDs = {}
        return clientCollectorUIDs

    def setClientCollectors(self, newClientCollectorsDict: dict) -> None:
        if not isinstance(newClientCollectorsDict, dict):
            self.MESSAGEHANDLER.error('Unable to save Collectors to Settings: Invalid format.')
            self.MESSAGEHANDLER.debug(f'Collectors argument: {newClientCollectorsDict}')
            self.MESSAGEHANDLER.debug(f'Collectors format: {str(type(newClientCollectorsDict))}')
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
        self.centralWidget().tabbedPane.facilitateResolution(f'Collector {collector_uid}', results)
        self.notifyUser(f"New entities discovered by collector: {collector_name}", "Collector Update")

    # Server functions
    def statusMessageListener(self, message: str, showPopup: bool = True) -> None:
        if showPopup:
            self.MESSAGEHANDLER.info(message, popUp=True)
        self.setStatus(message)

    def connectedToServerListener(self, server: str) -> None:
        self.setStatus(f"Connected to server: {server}")
        self.dockbarThree.serverStatus.updateStatus(f"Connected to server: {server}")
        self.SETTINGS.setValue("Project/Server", server)
        self.MESSAGEHANDLER.info("Communications successfully initialized with the server.", popUp=True)

    def connectToServer(self, password: str, server: str, port: int = 3777) -> None:
        self.setStatus("Connecting to server...")
        if self.FCOM.isConnected():
            self.disconnectFromServer()

        self.MESSAGEHANDLER.info(f"Connecting to server: {server}")
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
            self.MESSAGEHANDLER.error(f"Exception occurred while connecting to server: {repr(exception)}")
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
                    resolutionThread[0].deleteLater()
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
            duplicateExists = any(
                collectorInstance['uid'] == collector_uid
                for collectorInstance in self.runningCollectors[collector_category][collector_name]
            )
            if not duplicateExists:
                self.runningCollectors[collector_category][collector_name].append({'uid': collector_uid,
                                                                                   'entities': collector_entities,
                                                                                   'parameters': collector_parameters})
        currentCollectors = self.getClientCollectors()
        currentCollectors[collector_uid] = time.time_ns() // 1000
        self.setClientCollectors(currentCollectors)

    def stopRunningCollector(self, collectorUID: str):
        """
        Stops collector. Need to be ran before setClientCollectors.
        """
        with self.serverCollectorsLock:
            for collectorCategory in self.runningCollectors:
                for collectorName in self.runningCollectors[collectorCategory]:
                    for collector in self.runningCollectors[collectorCategory][collectorName]:
                        if collector['uid'] == collectorUID:
                            self.runningCollectors[collectorCategory][collectorName].remove(collector)

    def receiveProjectsListListener(self, projects: list) -> None:
        with self.serverProjectsLock:
            self.serverProjects = projects

    def receiveProjectCanvasesListListener(self, canvases: list) -> None:
        with self.syncedCanvasesLock:
            self.syncedCanvases = canvases

    def receiveProjectDeleteListener(self, deleted_project: str) -> None:
        with self.serverProjectsLock:
            with contextlib.suppress(ValueError):
                self.serverProjects.remove(deleted_project)
                self.closeServerProjectListener()

    def openServerProjectListener(self, project_name: str) -> None:
        self.SETTINGS.setValue("Project/Server/Project", project_name)
        self.setStatus(f"Opened Server Project: {project_name}")
        self.dockbarThree.serverStatus.updateStatus("Connected to server: " +
                                                    self.SETTINGS.value("Project/Server") + " Project: " + project_name)
        self.syncDatabase()
        self.FCOM.askProjectCanvasesList(project_name)
        self.FCOM.askServerForFileList(project_name)
        self.MESSAGEHANDLER.info(f"Opened Server Project: {project_name}", popUp=True)

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
            self.dockbarThree.serverStatus.updateStatus(f"Connected to server: {server}")
            if project_name != "":
                statusMessage = f"Closed Server project: {str(project_name)}"
                self.MESSAGEHANDLER.info(statusMessage)
                self.setStatus(statusMessage)

        self.dockbarOne.documentsList.updateFileListFromServer(None)
        with self.syncedCanvasesLock:
            self.syncedCanvases = []

    def openServerCanvasListener(self, canvas_name: str) -> None:
        project_name = self.SETTINGS.value("Project/Server/Project")
        self.setStatus(
            f"Opened Server Canvas: {canvas_name} on project: {project_name}"
        )
        self.dockbarThree.serverStatus.updateStatus("Connected to server: " +
                                                    self.SETTINGS.value("Project/Server") + " Project: " +
                                                    project_name + " Canvas: " + canvas_name)

    def closeServerCanvasListener(self, canvas_name: str) -> None:
        project_name = self.SETTINGS.value("Project/Server/Project")
        self.centralWidget().tabbedPane.unmarkSyncedCanvasesByName(canvas_name)
        self.setStatus(
            f"Closed Server Canvas: {canvas_name} on project: {project_name}"
        )
        self.dockbarThree.serverStatus.updateStatus("Connected to server: " +
                                                    self.SETTINGS.value("Project/Server") + " Project: " +
                                                    project_name)

    def syncDatabase(self):
        if self.FCOM.isConnected():
            project_name = self.SETTINGS.value("Project/Server/Project")
            if project_name != "":
                with self.LENTDB.dbLock:
                    self.FCOM.syncDatabase(project_name, self.LENTDB.database)
                self.MESSAGEHANDLER.info(f'Database Synced for project: {project_name}')

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
                    self.MESSAGEHANDLER.info(f'Syncing Canvas: {canvas_name}')
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
            statusMessage = f'Stopped syncing Canvas: {canvasName}'
        else:
            statusMessage = 'Stopped syncing all Canvases.'

        self.setStatus(statusMessage)
        self.MESSAGEHANDLER.info(statusMessage)

    def receiveSyncCanvasListener(self, canvas_name: str, canvas_nodes: dict, canvas_edges: dict) -> None:
        if canvas_name in self.centralWidget().tabbedPane.canvasTabs:
            canvasToSync = self.centralWidget().tabbedPane.canvasTabs[canvas_name]
            if canvasToSync.synced:
                canvasToSync.scene().syncCanvas(canvas_nodes, canvas_edges)
                self.MESSAGEHANDLER.debug(f'Canvas {canvas_name} synced.')

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
            self.MESSAGEHANDLER.debug(
                f'Project canvas {canvas_name} send update for entity / link: {str(entity_or_link_uid)}'
            )

    def receiveServerCanvasUpdate(self, canvas_name: str, entity_or_link_uid: Union[str, tuple]) -> None:
        scene = self.centralWidget().tabbedPane.getSceneByName(canvas_name)
        if scene is not None and entity_or_link_uid:
            if isinstance(entity_or_link_uid, str):
                # Add Entity
                if entity_or_link_uid not in scene.nodesDict:
                    scene.addNodeProgrammatic(entity_or_link_uid, fromServer=True)
                    scene.rearrangeGraph()
            elif entity_or_link_uid not in scene.linksDict:
                scene.addLinkProgrammatic(entity_or_link_uid, fromServer=True)
                scene.rearrangeGraph()

        self.MESSAGEHANDLER.debug(
            f'Received update to canvas: {canvas_name} for entity / link: {str(entity_or_link_uid)}'
        )

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
            self.MESSAGEHANDLER.debug(
                f'Sent database update to server: {entityJson} - Operation: {add}'
            )

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

        self.MESSAGEHANDLER.debug(
            f'Received database update from server: {entityJson} - Operation: {add}'
        )

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
        self.MESSAGEHANDLER.debug(f'Received file list from server: {fileList}')
        self.dockbarOne.documentsList.updateFileListFromServer(fileList)

    def fileUploadFinishedListener(self, file_name: str) -> None:
        self.MESSAGEHANDLER.debug(f'File upload finished: {file_name}')
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
                self.MESSAGEHANDLER.info(f'Asking question: {question}')
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
                    textAns += f"Answer {str(answerIndex + 1)}: {answer['answer']}\n\n" \
                               f"Context: ...{answer['context']}...\n\n" \
                               f"Document Used: {answer['doc']}\n\n"
                else:
                    textAns += f"Answer {str(answerIndex + 1)}: No Answer\n\n"

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
        # Have to show the window here, otherwise Seg Fault.
        self.show()

        self.restoreGeometry(QtCore.QByteArray(self.SETTINGS.value("MainWindow/Geometry")))
        self.restoreState(QtCore.QByteArray(self.SETTINGS.value("MainWindow/WindowState")))

        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea,
                           self.dockbarOne)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea,
                           self.dockbarTwo)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea,
                           self.dockbarThree)

        self.addToolBar(self.primaryToolbar)
        self.setMenuBar(MenuBar.MenuBar(self))

        # Set the main window title and show it to the user.
        self.resetMainWindowTitle()
        iconPath = Path(self.SETTINGS.value('Program/BaseDir')) / 'Icon.ico'
        appIcon = QtGui.QIcon(str(iconPath))
        self.setWindowIcon(appIcon)
        self.trayIcon = QtWidgets.QSystemTrayIcon(appIcon, self)
        # Whether the icon is shown or not depends on the Desktop environment.
        self.trayIcon.show()

        # Autosave approximately once every ten minutes.
        # Margin of error: 500 ms.
        self.saveTimer.start(600000)

        # Moved this here so the software doesn't crash if there are a ton of nodes.
        self.centralWidget().tabbedPane.open()
        self.RESOLUTIONMANAGER.loadMacros()
        # Creating default 'Home' tab, if no tabs exist.
        if len(self.centralWidget().tabbedPane.canvasTabs) == 0:
            self.centralWidget().tabbedPane.createHomeTab()

        self.setStatus("Ready")
        self.MESSAGEHANDLER.info(f"Project {self.SETTINGS.value('Project/Name', 'Untitled')} opened.")

        if self.SETTINGS.value("Program/Usage/First Time Start", 'true') == 'true':
            FirstTimeUseDialog().exec()
            #self.MODULEMANAGER.installSource({'URI': '', 'Remote': '', 'AuthType': None,
            #                                  'AuthCreds': None, 'SchemaType': '', 'UUID': str(uuid4())})
            self.SETTINGS.setValue("Program/Usage/First Time Start", 'false')

    def __init__(self):
        super(MainWindow, self).__init__()
        self.linkingNodes = False

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
                                              QtWidgets.QMessageBox.StandardButton.Ok)
                return
            except FileNotFoundError:
                QtWidgets.QMessageBox.warning(self, 'Cannot create project',
                                              'Cannot save project into a non-existing parent directory. '
                                              'Please create the required parent directories and try again.',
                                              QtWidgets.QMessageBox.StandardButton.Ok)
                return

        elif nW.openProject is not None:
            projectDir = Path(nW.openProject).parent.absolute()
            with open(nW.openProject, "rb") as projectDirFile:
                self.SETTINGS.load(load(projectDirFile))
            # Re-set file path related settings in case the project or the software was moved.
            self.SETTINGS.setValue("Program/BaseDir", dirname(abspath(getsourcefile(lambda: 0))))
            self.SETTINGS.setValue("Project/BaseDir", str(projectDir))
            self.SETTINGS.setValue("Project/FilesDir", str(projectDir / "Project Files"))

        self.MESSAGEHANDLER = MessageHandler.MessageHandler(self)
        self.MESSAGEHANDLER.info(f'Starting LinkScope Client, Version {self.SETTINGS.value("Program/Version", "N/A")}')
        self.URLMANAGER = URLManager.URLManager(self)
        self.dockbarThree = DockBarThree.DockBarThree(self)
        self.RESOURCEHANDLER = ResourceHandler.ResourceHandler(self)
        self.LENTDB = EntityDB.EntitiesDB(self)
        self.RESOLUTIONMANAGER = ResolutionManager.ResolutionManager(self)
        self.MODULEMANAGER = ModuleManager.ModulesManager(self)
        self.FCOM = FrontendCommunicationsHandler.CommunicationsHandler(self)
        self.LQLWIZARD = LQLQueryBuilder(self)

        # Have the project auto-save on regular intervals by default.
        self.saveTimer = QtCore.QTimer(self)
        self.saveTimer.timeout.connect(self.autoSaveProject)
        self.saveTimer.setSingleShot(False)
        self.saveTimer.setTimerType(QtCore.Qt.TimerType.VeryCoarseTimer)

        self.syncedCanvases = []
        self.syncedCanvasesLock = threading.Lock()
        self.serverProjects = []
        self.serverProjectsLock = threading.Lock()
        self.resolutions = []
        self.serverCollectorsLock = threading.Lock()
        self.collectors = {}
        self.runningCollectors = {}
        self.cycleExtractionThreads = []
        self.macrosLock = threading.Lock()
        self.runningMacros = []

        entityTextFont = QtGui.QFont(self.SETTINGS.value("Program/Graphics/Entity Text Font Type"),
                                     int(self.SETTINGS.value("Program/Graphics/Entity Text Font Size")),
                                     int(self.SETTINGS.value("Program/Graphics/Entity Text Font Boldness")))
        entityTextBrush = QtGui.QBrush(self.SETTINGS.value("Program/Graphics/Entity Text Color"))
        linkTextFont = QtGui.QFont(self.SETTINGS.value("Program/Graphics/Link Text Font Type"),
                                   int(self.SETTINGS.value("Program/Graphics/Link Text Font Size")),
                                   int(self.SETTINGS.value("Program/Graphics/Link Text Font Boldness")))
        linkTextBrush = QtGui.QBrush(self.SETTINGS.value("Program/Graphics/Link Text Color"))
        zoomHide = - int(self.SETTINGS.value("Program/Graphics/Label Fade Scroll Distance"))

        self.setCentralWidget(CentralPane.WorkspaceWidget(self,
                                                          self.MESSAGEHANDLER,
                                                          self.URLMANAGER,
                                                          self.LENTDB,
                                                          self.RESOURCEHANDLER,
                                                          entityTextFont,
                                                          entityTextBrush,
                                                          linkTextFont,
                                                          linkTextBrush,
                                                          zoomHide
                                                          ))

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

        # Allow threads to set statuses.
        self.statusBarSignalListener.connect(self.setStatus)

        # Allow threads to issue warnings.
        self.warningSignalListener.connect(self.MESSAGEHANDLER.warning)

        # Connect resolution results to macro execution function
        self.runningMacroResolutionFinishedSignalListener.connect(self.resolutionFinishedMacrosListener)

        self.initializeLayout()


class ReportWizard(QtWidgets.QWizard):
    def __init__(self, parent):
        super(ReportWizard, self).__init__(parent=parent)
        self.reportTempFolder = tempfile.mkdtemp()

        self.primaryFieldsList = []

        self.addPage(InitialConfigPage(self))
        self.addPage(TitlePage(self))

        self.addPage(SummaryPage(self))

        self.selectedNodes = [entity for entity in
                              self.parent().centralWidget().tabbedPane.getCurrentScene().selectedItems()
                              if isinstance(entity, BaseNode)]
        for selectedNode in self.selectedNodes:
            # used in wizard
            self.primaryField = selectedNode.labelItem.toPlainText()
            self.uid = selectedNode.uid

            # used in report generation
            self.primaryFieldsList.append(self.primaryField)
            self.addPage(EntityPage(self))

        self.setWizardStyle(QtWidgets.QWizard.WizardStyle.ModernStyle)
        self.setWindowTitle("Generate Report Wizard")

        self.button(QtWidgets.QWizard.WizardButton.FinishButton).clicked.connect(self.onFinish)

    def onFinish(self):
        outgoingEntitiesForEachEntity = []
        incomingEntitiesForEachEntity = []
        outgoingEntityPrimaryFieldsForEachEntity = []
        incomingEntityPrimaryFieldsForEachEntity = []

        entityList = []
        reportData = []
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
        canvasImagePath = Path(self.reportTempFolder) / 'canvas.png'
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
            self.parent().MESSAGEHANDLER.info(
                f"Saved Report at: {str(savePath)}", popUp=True
            )
        except PermissionError:
            self.parent().MESSAGEHANDLER.error(
                f"Could not generate report. No permission to save at the chosen location: {str(savePath)}",
                popUp=True,
                exc_info=False,
            )
        except Exception as exc:
            self.parent().MESSAGEHANDLER.error(
                f"Could not generate report: {str(exc)}", popUp=True, exc_info=True
            )
        finally:
            rmtree(self.reportTempFolder)


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
                                                             options=QtWidgets.QFileDialog.Option.DontUseNativeDialog)
        selectedPath = selectedPath[0]
        if selectedPath != '':
            savePath = Path(selectedPath).absolute()
            if savePath.suffix != '.pdf':
                savePath = savePath.with_suffix(f"{savePath.suffix}.pdf")
            self.savePathEdit.setText(str(savePath))

    def getData(self):
        return {'SavePath': self.savePathEdit.text()}


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
        return {
            'Title': self.inputTitleEdit.text(),
            'Subtitle': self.inputSubtitleEdit.text(),
            'Authors': self.inputAuthorsEdit.text(),
        }


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
        return {
            'SummaryNotes': self.inputNotesEdit.toPlainText(),
            'CanvasName': self.canvasDropDownMenu.currentText(),
            'ViewPort': self.viewPortCheckBox.isChecked(),
        }


class EntityPage(QtWidgets.QWizardPage):
    def __init__(self, parent: ReportWizard):
        super(EntityPage, self).__init__(parent=parent.parent())
        self.reportWizard = parent

        self.setTitle(self.tr("Entity Page Wizard"))
        self.setMinimumSize(300, 700)

        self.entityName = parent.primaryField
        self.entityUID = parent.uid

        self.inputNotesEdit = QtWidgets.QPlainTextEdit()
        self.inputImageEdit = QtWidgets.QLineEdit()
        self.inputImageEdit.setReadOnly(True)
        self.addAppendixButton = QtWidgets.QPushButton("Add New Appendix Section")
        self.removeAppendixButton = QtWidgets.QPushButton("Remove Last Appendix Section")

        self.scrolllayout = QtWidgets.QVBoxLayout()
        self.scrollwidget = QtWidgets.QWidget()

        self.defaultpic = self.parent().LENTDB.getEntity(self.entityUID).get('Icon')

        summaryLabel = QtWidgets.QLabel(f"Entity {self.entityName} Notes: ")

        imageLabel = QtWidgets.QLabel("Image Path: ")
        pDirButton = QtWidgets.QPushButton("Select Image...")
        pDirButton.clicked.connect(self.editPath)
        pDirButton.setDisabled(True)
        self.imageCheckBox = QtWidgets.QCheckBox('Add Custom Entity Image')
        self.imageCheckBox.setChecked(False)
        self.imageCheckBox.toggled.connect(pDirButton.setEnabled)

        self.addAppendixButton.clicked.connect(self.addSection)
        self.removeAppendixButton.clicked.connect(self.removeSection)

        self.scrollwidget.setLayout(self.scrolllayout)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.scrollwidget)

        hLayout = QtWidgets.QVBoxLayout()
        hLayout.addWidget(summaryLabel)
        hLayout.addWidget(self.inputNotesEdit)

        hLayout.addWidget(self.imageCheckBox)
        hLayout.addWidget(imageLabel)
        hLayout.addWidget(self.inputImageEdit)
        hLayout.addWidget(pDirButton)

        hLayout.addItem(QtWidgets.QSpacerItem(10, 30))
        hLayout.addWidget(self.addAppendixButton)
        hLayout.addWidget(self.removeAppendixButton)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(hLayout)
        layout.addWidget(scroll)

        self.setLayout(layout)

    def editPath(self) -> None:
        selectedPath = QtWidgets.QFileDialog().getOpenFileName(parent=self, caption='Select New Icon',
                                                               dir=str(Path.home()),
                                                               options=QtWidgets.QFileDialog.Option.DontUseNativeDialog,
                                                               filter="Image Files (*.png *.jpg)")[0]
        if selectedPath != '':
            self.inputImageEdit.setText(str(Path(selectedPath).absolute()))

    def addSection(self) -> None:
        appendixWidget = AppendixWidget()
        self.scrolllayout.addWidget(appendixWidget)

    def removeSection(self) -> None:
        if numChildren := self.scrolllayout.count():
            appendixItem = self.scrolllayout.takeAt(numChildren - 1)
            appendixItem.widget().deleteLater()

    def getData(self):
        appendixNotes = []
        if self.inputImageEdit.text() != '' and self.imageCheckBox.isChecked():
            data = {'EntityNotes': self.inputNotesEdit.toPlainText(), 'EntityImage': self.inputImageEdit.text()}
        elif 'PNG' in str(self.defaultpic):
            imagePath = Path(self.reportWizard.reportTempFolder) / f'{str(uuid4())}.png'
            with open(imagePath, 'wb') as tempFile:
                tempFile.write(bytearray(self.defaultpic.data()))

            data = {'EntityNotes': self.inputNotesEdit.toPlainText(), 'EntityImage': str(imagePath)}
        else:
            if 'svg' not in str(self.defaultpic):
                # Default picture is an SVG.
                self.defaultpic = self.parent().RESOURCEHANDLER.getEntityDefaultPicture(
                    self.parent().LENTDB.getEntity(self.entityUID)['Entity Type'])
            contents = bytearray(self.defaultpic)
            widthRegex = re.compile(b' width="\d*" ')
            fileContents = ''
            for widthMatches in widthRegex.findall(self.defaultpic):
                fileContents = contents.replace(widthMatches, b' ')
            heightRegex = re.compile(b' height="\d*" ')
            for heightMatches in heightRegex.findall(self.defaultpic):
                fileContents = contents.replace(heightMatches, b' ')
            fileContents = fileContents.replace(b'<svg ', b'<svg height="150" width="150" ')

            imagePath = Path(self.reportWizard.reportTempFolder) / f'{str(uuid4())}.svg'
            with open(imagePath, 'wb') as tempFile:
                tempFile.write(bytearray(fileContents))

            image = svg2rlg(imagePath)
            data = {'EntityNotes': self.inputNotesEdit.toPlainText(), 'EntityImage': image}

        for index in range(self.scrolllayout.count()):
            childWidget = self.scrolllayout.itemAt(index).widget()
            appendixDict = {'AppendixEntityNotes': childWidget.inputAppendixNotesEdit.toPlainText(),
                            'AppendixEntityImage': childWidget.inputAppendixImageEdit.text()}
            appendixNotes.append(appendixDict)
        return data, appendixNotes


class AppendixWidget(QtWidgets.QWidget):

    def __init__(self) -> None:
        super(AppendixWidget, self).__init__()
        appendixWidgetLayout = QtWidgets.QGridLayout()
        appendixLabelNotes = QtWidgets.QLabel("Entity Notes: ")
        self.inputAppendixNotesEdit = QtWidgets.QPlainTextEdit()
        imageAppendixLabel = QtWidgets.QLabel("Image Path: ")
        appendixButton = QtWidgets.QPushButton("Select Image...")
        appendixButton.clicked.connect(self.editAppendixPath)
        self.inputAppendixImageEdit = QtWidgets.QLineEdit()
        self.inputAppendixImageEdit.setReadOnly(True)
        appendixWidgetLayout.addWidget(appendixLabelNotes, 0, 0, 1, 1)
        appendixWidgetLayout.addWidget(self.inputAppendixNotesEdit, 2, 0, 4, 1)
        appendixWidgetLayout.addWidget(imageAppendixLabel, 7, 0, 1, 1)
        appendixWidgetLayout.addWidget(self.inputAppendixImageEdit, 9, 0, 1, 1)
        appendixWidgetLayout.addWidget(appendixButton, 11, 0, 1, 1)
        self.setLayout(appendixWidgetLayout)
        self.inputAppendixNotesEdit.setFixedHeight(100)

    def editAppendixPath(self) -> None:
        selectedPath = QtWidgets.QFileDialog().getOpenFileName(parent=self, caption='Select New Icon',
                                                               dir=str(Path.home()),
                                                               options=QtWidgets.QFileDialog.Option.DontUseNativeDialog,
                                                               filter="Image Files (*.png *.jpg)")[0]

        if selectedPath != '':
            self.inputAppendixImageEdit.setText(str(Path(selectedPath).absolute()))


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

        createCanvasTitleLabel.setFont(QtGui.QFont("Mono", 13, QtGui.QFont.Weight.Bold))

        createCanvasTitleLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
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
        dialogLayout.addWidget(spacer, 3, 1)

        openExistingCanvasTitleLabel = QtWidgets.QLabel("Open Existing Canvas")

        openExistingCanvasTitleLabel.setFont(QtGui.QFont("Mono", 13, QtGui.QFont.Weight.Bold))

        openExistingCanvasTitleLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        openExistingCanvasNameLabel = QtWidgets.QLabel("Canvas Name:")
        self.openExistingCanvasDropdown = QtWidgets.QComboBox()
        self.openExistingCanvasDropdown.setEditable(False)
        self.openExistingCanvasDropdown.SizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents)
        tabbedPane = self.parent().centralWidget().tabbedPane
        canvasTabs = tabbedPane.canvasTabs
        existingTabNames = [
            tabbedPane.tabText(tabIndex) for tabIndex in range(tabbedPane.count())
        ]
        openExistingCanvasButton = QtWidgets.QPushButton('Open Existing Canvas')
        openExistingCanvasButton.clicked.connect(self.confirmOpenExistingCanvas)

        canvasesToOpen = [tabName for tabName in canvasTabs if tabName not in existingTabNames]
        self.openExistingCanvasDropdown.addItems(canvasesToOpen)

        if not canvasesToOpen:
            self.openExistingCanvasDropdown.setEnabled(False)
            openExistingCanvasButton.setEnabled(False)

        dialogLayout.addWidget(openExistingCanvasTitleLabel, 4, 0, 1, 4)
        dialogLayout.addWidget(openExistingCanvasNameLabel, 5, 0, 1, 2)
        dialogLayout.addWidget(self.openExistingCanvasDropdown, 5, 2, 1, 2)
        dialogLayout.addWidget(openExistingCanvasButton, 6, 1, 1, 2)
        # Add some space in the layout
        spacer = QtWidgets.QLabel()
        dialogLayout.addWidget(spacer, 7, 1)

        openServerCanvasTitleLabel = QtWidgets.QLabel("Open Canvas From Server")

        openServerCanvasTitleLabel.setFont(QtGui.QFont("Mono", 13, QtGui.QFont.Weight.Bold))

        openServerCanvasTitleLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        openServerCanvasNameLabel = QtWidgets.QLabel("Canvas Name:")
        self.openServerCanvasDropdown = QtWidgets.QComboBox()
        self.openServerCanvasDropdown.setEditable(False)
        self.openServerCanvasDropdown.SizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents)
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
        if self.parent().centralWidget().tabbedPane.addCanvas(self.canvasName):
            self.accept()
        else:
            self.parent().MESSAGEHANDLER.warning("A Canvas with that name already exists!", popUp=True)

    def confirmOpenServerCanvas(self):
        self.canvasName = self.openServerCanvasDropdown.currentText()
        if self.parent().centralWidget().tabbedPane.addCanvas(self.canvasName):
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

        # New Project
        self.createProject = False
        newProjectNameLabel = QtWidgets.QLabel("New Project")
        newProjectNameLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        pProjectPathLabel = QtWidgets.QLabel("Project Path:")
        pDirLabel = QtWidgets.QLabel("Directory")
        pDirLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        pNameLabel = QtWidgets.QLabel("Name")
        pNameLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        pSlashLabel = QtWidgets.QLabel("/")
        pSlashLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.pName = QtWidgets.QLineEdit("Untitled")
        self.pDir = QtWidgets.QLineEdit("")
        self.pDir.setMinimumSize(400, 10)
        self.pDir.setReadOnly(True)

        pDirButton = QtWidgets.QPushButton("Select Directory...")
        pDirButton.clicked.connect(self.selectProjectDirectory)
        newProjectConfirm = QtWidgets.QPushButton("Create")

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
        openProjectFileLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        openProjectButton = QtWidgets.QPushButton("Open...")
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
        if not errorMessage:
            self.createProject = True
            self.close()
        else:
            showError = QtWidgets.QMessageBox(self)
            showError.setText(errorMessage)
            showError.setStandardButtons(QtWidgets.QMessageBox().StandardButton.Ok)
            showError.setDefaultButton(QtWidgets.QMessageBox().StandardButton.Ok)
            showError.exec()

    def selectProjectDirectory(self):

        filename = QtWidgets.QFileDialog.getExistingDirectory(self,
                                                              "Select Project Directory",
                                                              str(Path.home()),
                                                              options=QtWidgets.QFileDialog.Option.DontUseNativeDialog)
        if access(filename, R_OK | W_OK):
            self.pDir.setText(filename)

    def openFilename(self):

        filename = QtWidgets.QFileDialog.getOpenFileName(self,
                                                         "Open Project File",
                                                         str(Path.home()),
                                                         "LinkScope Projects(*.linkscope)",
                                                         options=QtWidgets.QFileDialog.Option.DontUseNativeDialog)

        if filename[0].endswith('.linkscope') and access(filename[0], R_OK | W_OK):
            self.openProject = filename[0]
            self.close()


class ResolutionExecutorThread(QtCore.QThread):
    sig = QtCore.Signal(str, list, str)
    sigStr = QtCore.Signal(str, str, str)
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
                self.sigError.emit(f'Resolution {self.resolution} failed during run.')
            elif isinstance(ret, bool):
                # Resolution is running on the server, we do not have results right now.
                ret = None
        except Exception as e:
            self.sigError.emit(f'Resolution {self.resolution} failed during run: {str(e)}')
            ret = None

        # If the resolution is ran on the server or there is a problem, don't emit signal.
        if ret is not None and self.return_results:
            if isinstance(ret, str):
                self.sigStr.emit(self.resolution, ret, self.uid)
            else:
                self.sig.emit(self.resolution, ret, self.uid)
            self.done = True


class ResolutionParametersSelector(QtWidgets.QDialog):

    def __init__(self, mainWindowObject, resolutionName, properties: dict, includeEntitySelector: list = None,
                 originTypes: list = None, resolutionDescription: str = None,
                 windowTitle: str = None) -> None:
        super(ResolutionParametersSelector, self).__init__()

        self.setModal(True)
        if windowTitle is None:
            windowTitle = f'Resolution Parameter Selector: {resolutionName}'
        self.setWindowTitle(windowTitle)
        self.parametersList = []
        # Have two separate dicts for readability.
        self.chosenParameters = {}
        self.properties = properties
        self.mainWindowObject = mainWindowObject
        self.resolutionName = resolutionName

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

            entitySelectTabLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            entitySelectTab.layout().addWidget(entitySelectTabLabel)

            self.entitySelector = QtWidgets.QListWidget()
            self.entitySelector.setSortingEnabled(True)
            self.entitySelector.addItems(includeEntitySelector)

            self.entitySelector.setSelectionMode(self.entitySelector.SelectionMode.MultiSelection)
            entitySelectTab.layout().addWidget(self.entitySelector)

            self.childWidget.addTab(entitySelectTab, 'Entities')

        for key in properties:
            propertyWidget = QtWidgets.QWidget()
            propertyKeyLayout = QtWidgets.QVBoxLayout()
            propertyWidget.setLayout(propertyKeyLayout)

            propertyLabel = QtWidgets.QLabel(properties[key].get('description'))
            propertyLabel.setWordWrap(True)
            propertyLabel.setMaximumWidth(600)

            propertyLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
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

            rememberChoiceCheckbox = QtWidgets.QCheckBox('Remember Choice')
            rememberChoiceCheckbox.setChecked(False)
            propertyKeyLayout.addWidget(rememberChoiceCheckbox)
            propertyKeyLayout.setStretch(1, 1)

            self.childWidget.addTab(propertyWidget, key)
            self.parametersList.append((key, propertyInputField, rememberChoiceCheckbox))

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
        savedParameters = {}
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
                savedParameters[resolutionParameterName] = value

        # Only save parameters after we verify that everything is filled in properly.
        for savedParameter in savedParameters:
            if self.properties[savedParameter].get('global') is True:
                self.mainWindowObject.SETTINGS.setGlobalValue(
                    f'Resolutions/Global/Parameters/{savedParameter}',
                    savedParameters[savedParameter],
                )
            else:
                self.mainWindowObject.SETTINGS.setGlobalValue(
                    f'Resolutions/{self.resolutionName}/{savedParameter}',
                    savedParameters[savedParameter],
                )

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

        editDialogLayout = QtWidgets.QGridLayout()
        self.setLayout(editDialogLayout)
        scrollArea = QtWidgets.QScrollArea()
        scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
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

        resolutionCategoryLabel.setFont(QtGui.QFont("Mono", 13, QtGui.QFont.Weight.Bold))
        resolutionCategoryLabel.setFrameStyle(QtWidgets.QFrame.Shadow.Raised | QtWidgets.QFrame.Shape.Panel)

        resolutionCategoryLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        scrollLayout.addWidget(resolutionCategoryLabel)
        scrollLayout.addWidget(resolutionCategoryWidget)

        confirmButton = QtWidgets.QPushButton('Confirm')
        confirmButton.clicked.connect(self.accept)
        editDialogLayout.addWidget(confirmButton, 2, 1, 1, 1)
        cancelButton = QtWidgets.QPushButton('Cancel')
        cancelButton.clicked.connect(self.reject)
        editDialogLayout.addWidget(cancelButton, 2, 0, 1, 1)

        self.settingsTextboxes = []
        self.settingsValueTextboxes = []
        self.newSettings = {}

        etfSettingTextbox = SettingsIntegerEditTextBox(
            int(self.settings.value("Program/Graphics/Entity Text Font Size")),
            "ETF",
            50, 5)
        self.settingsValueTextboxes.append(etfSettingTextbox)
        self.resolutionCategoryLayout.addRow("Entity Text Font Size", etfSettingTextbox)

        ltfSettingTextbox = SettingsIntegerEditTextBox(
            int(self.settings.value("Program/Graphics/Link Text Font Size")),
            "LTF",
            50, 5)
        self.settingsValueTextboxes.append(ltfSettingTextbox)
        self.resolutionCategoryLayout.addRow("Link Text Font Size", ltfSettingTextbox)

        labelFadeSettingTextbox = SettingsIntegerEditTextBox(
            int(self.settings.value("Program/Graphics/Label Fade Scroll Distance")),
            "LF",
            12, 0)
        self.settingsValueTextboxes.append(labelFadeSettingTextbox)
        self.resolutionCategoryLayout.addRow("Label Fade Threshold", labelFadeSettingTextbox)

        etcSettingWidget = QtWidgets.QWidget()
        etcSettingLayout = QtWidgets.QHBoxLayout()
        etcSettingWidget.setLayout(etcSettingLayout)

        etcSettingTextbox = SettingsEditTextBox(self.settings.value("Program/Graphics/Entity Text Color"), "ETC")
        etcSettingTextbox.setToolTip('Hex color code')
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

        ltcSettingTextbox = SettingsEditTextBox(self.settings.value("Program/Graphics/Link Text Color"), "LTC")
        ltcSettingTextbox.setToolTip('Hex color code')
        ltcSettingLayout.addWidget(ltcSettingTextbox, 5)

        ltcSettingPalettePrompt = QtWidgets.QPushButton(QtGui.QIcon(resourceHandler.getIcon("colorPicker")),
                                                        "Pick Colour")
        ltcSettingPalettePrompt.clicked.connect(self.runLinkColorPicker)
        ltcSettingLayout.addWidget(ltcSettingPalettePrompt)

        self.settingsTextboxes.append(ltcSettingTextbox)
        self.resolutionCategoryLayout.addRow("Link Text Color", ltcSettingWidget)

    def runEntityColorPicker(self):
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor(self.settings.value("Program/Graphics/Entity Text Color")),
                                                title="Select New Entity Text Color")
        if color.isValid():
            self.settingsTextboxes[0].setText(color.name())

    def runLinkColorPicker(self):
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor(self.settings.value("Program/Graphics/Link Text Color")),
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

    def __init__(self, mainWindowObject):
        super(ProgramEditDialog, self).__init__()
        self.setModal(True)
        self.setMaximumWidth(850)
        self.setMinimumWidth(600)
        self.setMaximumHeight(600)
        self.setMinimumHeight(400)
        self.mainWindow = mainWindowObject

        resolutionsEditDialog = QtWidgets.QGridLayout()
        self.setLayout(resolutionsEditDialog)
        scrollArea = QtWidgets.QScrollArea()
        scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scrollArea.setWidgetResizable(True)
        scrollContainer = QtWidgets.QWidget()
        scrollLayout = QtWidgets.QVBoxLayout()
        scrollContainer.setLayout(scrollLayout)
        scrollArea.setWidget(scrollContainer)
        resolutionsEditDialog.addWidget(scrollArea, 0, 0, 2, 2)

        resolutionCategoryWidget = QtWidgets.QWidget()
        self.resolutionCategoryLayout = SettingsCategoryLayout(supportsDeletion=False)
        resolutionCategoryWidget.setLayout(self.resolutionCategoryLayout)
        resolutionCategoryLabel = QtWidgets.QLabel('Program Settings')

        resolutionCategoryLabel.setFont(QtGui.QFont("Mono", 13, QtGui.QFont.Weight.Bold))
        resolutionCategoryLabel.setFrameStyle(QtWidgets.QFrame.Shadow.Raised | QtWidgets.QFrame.Shape.Panel)

        resolutionCategoryLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        scrollLayout.addWidget(resolutionCategoryLabel)
        scrollLayout.addWidget(resolutionCategoryWidget)

        confirmButton = QtWidgets.QPushButton('Confirm')
        confirmButton.clicked.connect(self.accept)
        resolutionsEditDialog.addWidget(confirmButton, 2, 1, 1, 1)
        cancelButton = QtWidgets.QPushButton('Cancel')
        cancelButton.clicked.connect(self.reject)
        resolutionsEditDialog.addWidget(cancelButton, 2, 0, 1, 1)

        self.settingsTextboxes = []
        self.newSettings = {}
        self.settingsSingleChoice = []
        self.torProfileTextBox = None

        for setting, settingValue in self.mainWindow.SETTINGS.getGroupSettings('Program/').items():
            keyName = setting.split('Program/', 1)[1]
            # Don't allow users to mess with sensitive settings.
            if keyName not in ["BaseDir", "Version", "Macros"] and len(setting.split('/')) == 2:
                # A bit redundant to do it this way, but it'll be cleaner if / when more settings are added.
                if keyName == "Graph Layout":
                    settingSingleChoice = SettingsEditSingleChoice(['dot', 'sfdp', 'neato'],
                                                                   settingValue,
                                                                   setting)
                    self.settingsSingleChoice.append(settingSingleChoice)
                    self.resolutionCategoryLayout.addRow(keyName, settingSingleChoice)
                elif keyName == "TOR Profile Location":
                    self.torProfileTextBox = SettingsEditTextBox(settingValue, setting)
                    self.settingsTextboxes.append(self.torProfileTextBox)
                    torValueWidget = QtWidgets.QWidget()
                    torValueWidgetLayout = QtWidgets.QHBoxLayout()
                    torValueWidget.setLayout(torValueWidgetLayout)
                    torValueWidgetLayout.addWidget(self.torProfileTextBox)
                    fileSelectButton = QtWidgets.QPushButton('Select Folder')
                    fileSelectButton.clicked.connect(self.getTORProfileLocation)
                    torValueWidgetLayout.addWidget(fileSelectButton)

                    self.resolutionCategoryLayout.addRow(keyName, torValueWidget)

                else:
                    settingTextbox = SettingsEditTextBox(settingValue, setting)
                    self.settingsTextboxes.append(settingTextbox)
                    self.resolutionCategoryLayout.addRow(keyName, settingTextbox)

    def getTORProfileLocation(self):
        getTORProfileDialog = QtWidgets.QFileDialog()
        getTORProfileDialog.setOption(QtWidgets.QFileDialog.Option.DontUseNativeDialog, True)
        getTORProfileDialog.setViewMode(QtWidgets.QFileDialog.ViewMode.List)
        getTORProfileDialog.setFileMode(QtWidgets.QFileDialog.FileMode.Directory)
        getTORProfileDialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptOpen)
        getTORProfileDialog.setDirectory(str(Path.home()))

        if getTORProfileDialog.exec():
            try:
                filePath = Path(getTORProfileDialog.selectedFiles()[0])
                # Basic sanity check.
                if not (filePath / 'sessionstore-backups').exists():
                    self.mainWindow.MESSAGEHANDLER.error('Path selected is not a TOR browser profile.\n'
                                                         'TOR operations may not work.', exc_info=False)
                self.torProfileTextBox.setText(str(filePath.absolute()))
            except Exception:
                self.mainWindow.MESSAGEHANDLER.info('TOR profile path selection cancelled.')

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

        resolutionsEditDialog = QtWidgets.QGridLayout()
        self.setLayout(resolutionsEditDialog)
        scrollArea = QtWidgets.QScrollArea()
        scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
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

        resolutionCategoryLabel.setFont(QtGui.QFont("Mono", 13, QtGui.QFont.Weight.Bold))
        resolutionCategoryLabel.setFrameStyle(QtWidgets.QFrame.Shadow.Raised | QtWidgets.QFrame.Shape.Panel)

        resolutionCategoryLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        scrollLayout.addWidget(resolutionCategoryLabel)
        scrollLayout.addWidget(resolutionCategoryWidget)

        confirmButton = QtWidgets.QPushButton('Confirm')
        confirmButton.clicked.connect(self.accept)
        resolutionsEditDialog.addWidget(confirmButton, 2, 1, 1, 1)
        cancelButton = QtWidgets.QPushButton('Cancel')
        cancelButton.clicked.connect(self.reject)
        resolutionsEditDialog.addWidget(cancelButton, 2, 0, 1, 1)

        self.settingsTextboxes = []
        self.newSettings = {}

        for setting, settingValue in self.settings.getGroupSettings('Resolutions/').items():
            keyName = setting.split('Resolutions/', 1)[1]
            settingTextbox = SettingsEditTextBox(settingValue, setting)
            self.settingsTextboxes.append(settingTextbox)
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

        loggingSettingsLayout = QtWidgets.QGridLayout()
        self.setLayout(loggingSettingsLayout)
        scrollArea = QtWidgets.QScrollArea()
        scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
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

        loggingCategoryLabel.setFont(QtGui.QFont("Mono", 13, QtGui.QFont.Weight.Bold))
        loggingCategoryLabel.setFrameStyle(QtWidgets.QFrame.Shadow.Raised | QtWidgets.QFrame.Shape.Panel)

        loggingCategoryLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        scrollLayout.addWidget(loggingCategoryLabel)
        scrollLayout.addWidget(loggingCategoryWidget)

        confirmButton = QtWidgets.QPushButton('Confirm')
        confirmButton.clicked.connect(self.accept)
        loggingSettingsLayout.addWidget(confirmButton, 2, 1, 1, 1)
        cancelButton = QtWidgets.QPushButton('Cancel')
        cancelButton.clicked.connect(self.reject)
        loggingSettingsLayout.addWidget(cancelButton, 2, 0, 1, 1)

        self.settingsTextboxes = []
        self.newSettings = {}

        for setting, settingValue in self.settings.getGroupSettings('Logging/').items():
            settingTextbox = SettingsEditTextBox(settingValue, setting)
            self.settingsTextboxes.append(settingTextbox)
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

        editDialogLayout = QtWidgets.QGridLayout()
        self.setLayout(editDialogLayout)
        scrollArea = QtWidgets.QScrollArea()
        scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
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

        resolutionCategoryLabel.setFont(QtGui.QFont("Mono", 13, QtGui.QFont.Weight.Bold))
        resolutionCategoryLabel.setFrameStyle(QtWidgets.QFrame.Shadow.Raised | QtWidgets.QFrame.Shape.Panel)

        resolutionCategoryLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        scrollLayout.addWidget(resolutionCategoryLabel)
        scrollLayout.addWidget(resolutionCategoryWidget)

        confirmButton = QtWidgets.QPushButton('Confirm')
        confirmButton.clicked.connect(self.accept)
        editDialogLayout.addWidget(confirmButton, 2, 1, 1, 1)
        cancelButton = QtWidgets.QPushButton('Cancel')
        cancelButton.clicked.connect(self.reject)
        editDialogLayout.addWidget(cancelButton, 2, 0, 1, 1)

        self.settingsTextboxes = []
        self.settingsSingleChoice = []
        self.newSettings = {}

        for setting, settingValue in self.settings.getGroupSettings('Project/').items():
            keyName = setting.split('Project/', 1)[1]
            if keyName == 'Resolution Result Grouping Threshold' or \
                    setting == 'Number of Answers Returned' or \
                    setting == 'Question Answering Retriever Value' or \
                    setting == 'Question Answering Reader Value':
                settingTextbox = SettingsEditTextBox(settingValue, setting)
                self.settingsTextboxes.append(settingTextbox)
                self.resolutionCategoryLayout.addRow(keyName, settingTextbox)

            elif keyName == 'Symlink or Copy Materials':
                settingSingleChoice = SettingsEditSingleChoice(['Symlink', 'Copy'], settingValue, setting)
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
        super(SettingsEditTextBox, self).__init__(contents)
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
        self.layout().setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

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

        keyLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
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

        findLabel = QtWidgets.QLabel('Find:')

        findLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.findInput = QtWidgets.QLineEdit('')
        self.findInput.setPlaceholderText('Type the primary field value to search for')

        confirmButton = QtWidgets.QPushButton('Confirm')
        confirmButton.clicked.connect(self.accept)
        cancelButton = QtWidgets.QPushButton('Cancel')
        cancelButton.clicked.connect(self.reject)

        autoCompleter = QtWidgets.QCompleter(primaryFieldsList)
        if regex:
            # Doesn't actually work in python, as far as I can see.
            # Throws error:  Unhandled QCompleter::filterMode flag is used.
            # autoCompleter.setFilterMode(QtGui.Qt.MatchRegularExpression)
            pass
        else:
            autoCompleter.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
            autoCompleter.setFilterMode(QtCore.Qt.MatchFlag.MatchContains)
        self.findInput.setCompleter(autoCompleter)

        findLayout = QtWidgets.QGridLayout()
        self.setLayout(findLayout)

        findLayout.addWidget(findLabel, 0, 0, 1, 1)
        findLayout.addWidget(self.findInput, 0, 1, 1, 1)
        # Adding the confirm button first so that it's what is activated when someone presses Enter.
        findLayout.addWidget(confirmButton, 1, 1, 1, 1)
        findLayout.addWidget(cancelButton, 1, 0, 1, 1)


class FindEntityOfTypeOnCanvasDialog(QtWidgets.QDialog):

    def __init__(self, mainWindowObject, entityTypesDict: dict, regex: bool):
        super(FindEntityOfTypeOnCanvasDialog, self).__init__()
        self.setModal(True)
        self.setMinimumWidth(400)
        if regex:
            self.setWindowTitle('Regex Find Entity Of Type')
        else:
            self.setWindowTitle('Find Entity Of Type')

        typeLabel = QtWidgets.QLabel('Entity Type:')
        self.typeInput = QtWidgets.QComboBox()
        self.typeInput.setEditable(False)
        self.typeInput.addItems(list(entityTypesDict))
        self.typeInput.currentIndexChanged.connect(self.changeSelectedType)
        findLabel = QtWidgets.QLabel('Find Entity:')

        findLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.findInput = QtWidgets.QLineEdit('')
        self.findInput.setPlaceholderText('Type the primary field value to search for')

        confirmButton = QtWidgets.QPushButton('Confirm')
        confirmButton.clicked.connect(self.accept)
        cancelButton = QtWidgets.QPushButton('Cancel')
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
                autoCompleter.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
                autoCompleter.setFilterMode(QtCore.Qt.MatchFlag.MatchContains)

        findLayout = QtWidgets.QGridLayout()
        self.setLayout(findLayout)

        findLayout.addWidget(typeLabel, 0, 0, 1, 1)
        findLayout.addWidget(self.typeInput, 0, 1, 1, 1)
        findLayout.addWidget(findLabel, 1, 0, 1, 1)
        findLayout.addWidget(self.findInput, 1, 1, 1, 1)
        # Adding the confirm button first so that it's what is activated when someone presses Enter.
        findLayout.addWidget(confirmButton, 2, 1, 1, 1)
        findLayout.addWidget(cancelButton, 2, 0, 1, 1)

        try:
            self.changeSelectedType()
        except KeyError:
            mainWindowObject.MESSAGEHANDLER.error('No Nodes present on current canvas.', popUp=True, exc_info=False)
            return

    def changeSelectedType(self):
        self.findInput.setCompleter(self.autoCompleters[self.typeInput.currentText()])


class ResolutionSearchResultsList(QtWidgets.QListWidget):

    def __init__(self, mainWindowObject: MainWindow):
        super(ResolutionSearchResultsList, self).__init__()
        self.mainWindow = mainWindowObject
        self.setSortingEnabled(True)

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
        for category in self.resolutions:
            for resolution in self.resolutions[category]:
                if target == 'Any':
                    validResolutions.append(f'{category}/{resolution}')

                elif target in self.resolutions[category][resolution]['originTypes']:
                    validResolutions.append(f'{category}/{resolution}')
        origin = self.originDropDown.currentText()
        if origin != 'Any':
            for category in self.resolutions:
                for resolution in self.resolutions[category]:
                    if origin not in self.resolutions[category][resolution]['originTypes']:
                        with contextlib.suppress(KeyError):
                            validResolutions.remove(f'{str(category)}/{str(resolution)}')
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
                            with contextlib.suppress(KeyError):
                                validResolutions.remove(f'{str(category)}/{str(resolution)}')
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
        cancelButton = QtWidgets.QPushButton('Cancel')
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
        isPrimaryRadioButton.setText(entityJSON[list(entityJSON)[1]])

        self.entitiesTable.setCellWidget(newRowIndex, 0, isPrimaryRadioButton)

        pixmapLabel = QtWidgets.QLabel()
        entityPixmap = QtGui.QPixmap()
        entityPixmap.loadFromData(entityJSON.get('Icon'))
        pixmapLabel.setPixmap(entityPixmap)

        pixmapLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        entityTypeWidget = QtWidgets.QWidget()
        entityTypeWidgetLayout = QtWidgets.QHBoxLayout()
        entityTypeWidget.setLayout(entityTypeWidgetLayout)
        entityTypeWidgetLayout.addWidget(pixmapLabel)
        entityTypeWidgetLayout.addWidget(QtWidgets.QLabel(entityJSON['Entity Type']))

        self.entitiesTable.setCellWidget(newRowIndex, 1, entityTypeWidget)

        incomingLinks = QtWidgets.QLabel(str(len(self.parent.LENTDB.getIncomingLinks(entityJSON['uid']))))

        incomingLinks.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.entitiesTable.setCellWidget(newRowIndex, 2, incomingLinks)
        outgoingLinks = QtWidgets.QLabel(str(len(self.parent.LENTDB.getOutgoingLinks(entityJSON['uid']))))

        outgoingLinks.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.entitiesTable.setCellWidget(newRowIndex, 3, outgoingLinks)

        upDownButtons = MergeTableShiftRowUpDownButtons(self.entitiesTable, entityJSON['uid'])

        self.entitiesTable.setCellWidget(newRowIndex, 4, upDownButtons)

    def accept(self) -> None:
        for rowIndex in range(self.entitiesTable.rowCount()):
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
        widgetsToShift = [
            self.cellWidget(rowIndex, widgetColumnIndex)
            for widgetColumnIndex in range(5)
        ]
        self.insertRow(rowIndex - 1)
        self.setRowHeight(rowIndex - 1, 70)
        for widgetColumnIndex in range(5):
            self.setCellWidget(rowIndex - 1, widgetColumnIndex, widgetsToShift[widgetColumnIndex])
        self.removeRow(rowIndex + 1)

    def shiftRowDown(self, widget: QtWidgets.QWidget) -> None:
        rowIndex = self.findRowOfShiftingWidget(widget)
        if rowIndex == self.rowCount() - 1:
            return
        widgetsToShift = [
            self.cellWidget(rowIndex, widgetColumnIndex)
            for widgetColumnIndex in range(5)
        ]
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

        downButton = QtWidgets.QPushButton('v')

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

        for count, link in enumerate(self.allLinks, start=1):
            selectResolution = QtWidgets.QCheckBox(link['Resolution'])
            selectResolution.linkUID = link['uid']
            self.entitiesTable.setCellWidget(newRowIndex, count, selectResolution)

    def removeRow(self) -> None:
        self.entitiesTable.removeRow(self.entitiesTable.rowCount() - 1)

    def accept(self) -> None:
        for newEntityRow in range(self.entitiesTable.rowCount()):
            entityName = self.entitiesTable.item(newEntityRow, 0).text()
            if entityName == '':
                self.parent.MESSAGEHANDLER.info('Cannot split into entities with blank primary fields.',
                                                popUp=True)
                return self.clearSplitEntitiesHelper()
            elif self.parent.LENTDB.doesEntityExist(entityName) and entityName != self.entityToSplitPrimaryField:
                self.parent.MESSAGEHANDLER.info("Entity primary field value specified already exists:\n" + entityName,
                                                popUp=True)
                return self.clearSplitEntitiesHelper()
            elif entityName in self.splitEntities:
                self.parent.MESSAGEHANDLER.info("Duplicate primary field value specified:\n" + entityName,
                                                popUp=True)
                return self.clearSplitEntitiesHelper()
            self.splitEntities.append(entityName)

            allLinkUIDsForEntity = [
                self.allLinks[columnIndex - 1]
                for columnIndex in range(1, self.entitiesTable.columnCount())
                if self.entitiesTable.cellWidget(
                    newEntityRow, columnIndex
                ).isChecked()
            ]
            self.splitEntitiesWithLinks.append((entityName, allLinkUIDsForEntity))

        # Clear out this list, no more need for it
        self.splitEntities = []
        super(SplitEntitiesDialog, self).accept()

    def clearSplitEntitiesHelper(self):
        self.splitEntities = []
        self.splitEntitiesWithLinks = []
        return


class QueryBuilderWizard(QtWidgets.QDialog):

    def __init__(self, mainWindowObject: MainWindow):
        super(QueryBuilderWizard, self).__init__()
        self.mainWindowObject = mainWindowObject
        self.setModal(True)
        self.setWindowTitle('LQL Query Wizard')
        dialogLayout = QtWidgets.QGridLayout()
        self.setLayout(dialogLayout)

        # Add a tab to create a new query, and a tab to re-run old queries.
        self.queryNewOrHistory = QtWidgets.QTabWidget()
        self.queryTabbedPane = QtWidgets.QTabWidget()
        self.queryNewOrHistory.addTab(self.queryTabbedPane, 'New Query')
        dialogLayout.addWidget(self.queryNewOrHistory)

        buttonsWidget = QtWidgets.QWidget()
        buttonsWidgetLayout = QtWidgets.QHBoxLayout()
        buttonsWidget.setLayout(buttonsWidgetLayout)
        exitButton = QtWidgets.QPushButton('Close')
        exitButton.clicked.connect(self.accept)
        resetWizardButton = QtWidgets.QPushButton('Reset Wizard')
        resetWizardButton.clicked.connect(self.updateValues)
        self.runButton = QtWidgets.QPushButton('Run Query')
        self.runButton.clicked.connect(self.runQuery)
        buttonsWidgetLayout.addWidget(exitButton)
        buttonsWidgetLayout.addWidget(resetWizardButton)
        buttonsWidgetLayout.addWidget(self.runButton)
        dialogLayout.addWidget(buttonsWidget)
        self.runButton.setDefault(True)

        #### SELECT
        selectPane = QtWidgets.QWidget()
        selectPaneLayout = QtWidgets.QGridLayout()
        selectPane.setLayout(selectPaneLayout)
        self.selectStatementPicker = QtWidgets.QComboBox()
        self.selectStatementPicker.addItems(['SELECT', 'RSELECT'])
        self.selectStatementPicker.setEditable(False)  # Default, but it's nice to be explicit.
        self.selectStatementPicker.currentIndexChanged.connect(
            lambda newIndex: self.selectStatementValuePickerLayout.setCurrentIndex(newIndex))
        selectStatementValuePickerWidget = QtWidgets.QWidget()
        self.selectStatementValuePickerLayout = QtWidgets.QStackedLayout()
        selectStatementValuePickerWidget.setLayout(self.selectStatementValuePickerLayout)
        self.selectStatementList = QtWidgets.QListWidget()
        self.selectStatementList.setSortingEnabled(True)
        self.selectStatementList.setSelectionMode(QtWidgets.QListWidget.SelectionMode.ExtendedSelection)
        self.selectStatementList.setMinimumHeight(125)
        self.selectStatementList.setToolTip('Highlight all the fields you wish to select.')
        self.selectStatementTextbox = QtWidgets.QLineEdit('')
        self.selectStatementTextbox.setFixedHeight(26)
        self.selectStatementTextbox.setToolTip('Type the regex you want to use to specify the fields to select.')
        self.selectStatementValuePickerLayout.addWidget(self.selectStatementList)
        self.selectStatementValuePickerLayout.addWidget(self.selectStatementTextbox)

        selectPaneLayout.addWidget(QtWidgets.QLabel('Selection mode: '), 0, 0, 1, 1)
        selectPaneLayout.addWidget(self.selectStatementPicker, 0, 1, 1, 1)
        selectPaneLayout.addWidget(QtWidgets.QLabel('Field selection:'), 1, 0, 1, 2)
        selectPaneLayout.addWidget(selectStatementValuePickerWidget, 2, 0, 2, 2)

        self.queryTabbedPane.addTab(selectPane, 'Selection')
        ####

        #### SOURCE
        sourcePane = QtWidgets.QWidget()
        sourcePaneLayout = QtWidgets.QGridLayout()
        sourcePane.setLayout(sourcePaneLayout)

        self.sourceStatementPicker = QtWidgets.QComboBox()
        self.sourceStatementPicker.addItems(['FROMDB', 'FROM'])
        self.sourceStatementPicker.setEditable(False)
        self.sourceStatementPicker.currentTextChanged.connect(self.sourceModeSwitch)

        self.sourceValues = []
        self.sourceValuesArea = QtWidgets.QScrollArea()
        self.sourceValuesArea.setWidgetResizable(True)
        self.sourceValuesArea.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum)

        sourceValuesAreaWidget = QtWidgets.QWidget()
        self.sourceValuesAreaWidgetLayout = QtWidgets.QVBoxLayout()
        sourceValuesAreaWidget.setLayout(self.sourceValuesAreaWidgetLayout)
        self.sourceValuesArea.setWidget(sourceValuesAreaWidget)
        self.sourceValuesArea.setEnabled(False)
        self.sourceValuesArea.setDisabled(True)
        self.sourceValuesArea.setHidden(True)

        sourceButtonsWidget = QtWidgets.QWidget()
        sourceButtonsWidgetLayout = QtWidgets.QHBoxLayout()
        sourceButtonsWidget.setLayout(sourceButtonsWidgetLayout)
        sourceAddStatementButton = QtWidgets.QPushButton('Add Clause')
        sourceRemoveStatementButton = QtWidgets.QPushButton('Remove Last Clause')
        sourceAddStatementButton.clicked.connect(self.addSourceClause)
        sourceRemoveStatementButton.clicked.connect(self.removeSourceClause)
        sourceButtonsWidgetLayout.addWidget(sourceRemoveStatementButton)
        sourceButtonsWidgetLayout.addWidget(sourceAddStatementButton)

        self.sourceValuesAreaWidgetLayout.addWidget(sourceButtonsWidget)

        sourcePaneLayout.addWidget(QtWidgets.QLabel('Source: '), 0, 0, 1, 1)
        sourcePaneLayout.addWidget(self.sourceStatementPicker, 0, 1, 1, 1)
        sourcePaneLayout.addWidget(self.sourceValuesArea, 1, 0, 2, 2)

        self.queryTabbedPane.addTab(sourcePane, 'Source')
        ####

        #### CONDITIONS
        conditionsPane = QtWidgets.QWidget()
        conditionsPaneLayout = QtWidgets.QGridLayout()
        conditionsPane.setLayout(conditionsPaneLayout)

        self.conditionValues = []
        self.conditionValuesArea = QtWidgets.QScrollArea()
        self.conditionValuesArea.setWidgetResizable(True)
        conditionValuesAreaWidget = QtWidgets.QWidget()
        self.conditionValuesAreaWidgetLayout = QtWidgets.QVBoxLayout()
        conditionValuesAreaWidget.setLayout(self.conditionValuesAreaWidgetLayout)
        self.conditionValuesArea.setWidget(conditionValuesAreaWidget)
        self.conditionValuesArea.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum,
                                               QtWidgets.QSizePolicy.Policy.Minimum)

        conditionsButtonsWidget = QtWidgets.QWidget()
        conditionsButtonsWidgetLayout = QtWidgets.QHBoxLayout()
        conditionsButtonsWidget.setLayout(conditionsButtonsWidgetLayout)
        conditionsAddStatementButton = QtWidgets.QPushButton('Add Condition')
        conditionsRemoveStatementButton = QtWidgets.QPushButton('Remove Last Condition')
        conditionsAddStatementButton.clicked.connect(self.addConditionClause)
        conditionsRemoveStatementButton.clicked.connect(self.removeConditionClause)
        conditionsButtonsWidgetLayout.addWidget(conditionsRemoveStatementButton)
        conditionsButtonsWidgetLayout.addWidget(conditionsAddStatementButton)

        self.conditionValuesAreaWidgetLayout.addWidget(conditionsButtonsWidget)

        conditionsPaneLayout.addWidget(QtWidgets.QLabel('Conditions: '), 0, 0, 1, 1)
        conditionsPaneLayout.addWidget(self.conditionValuesArea, 0, 0, 2, 2)

        self.queryTabbedPane.addTab(conditionsPane, 'Conditions')
        ####

        #### MODIFY
        modificationsPane = QtWidgets.QWidget()
        modificationsPaneLayout = QtWidgets.QGridLayout()
        modificationsPane.setLayout(modificationsPaneLayout)

        self.modificationValues = []
        self.modificationValuesArea = QtWidgets.QScrollArea()
        self.modificationValuesArea.setWidgetResizable(True)
        self.modificationValuesArea.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum,
                                                  QtWidgets.QSizePolicy.Policy.Minimum)

        modificationValuesAreaWidget = QtWidgets.QWidget()
        self.modificationValuesAreaWidgetLayout = QtWidgets.QVBoxLayout()
        modificationValuesAreaWidget.setLayout(self.modificationValuesAreaWidgetLayout)
        self.modificationValuesArea.setWidget(modificationValuesAreaWidget)

        modificationsButtonsWidget = QtWidgets.QWidget()
        modificationsButtonsWidgetLayout = QtWidgets.QHBoxLayout()
        modificationsButtonsWidget.setLayout(modificationsButtonsWidgetLayout)
        modificationsAddStatementButton = QtWidgets.QPushButton('Add Modification')
        modificationsRemoveStatementButton = QtWidgets.QPushButton('Remove Last Modification')
        modificationsAddStatementButton.clicked.connect(self.addModificationClause)
        modificationsRemoveStatementButton.clicked.connect(self.removeModificationClause)
        modificationsButtonsWidgetLayout.addWidget(modificationsRemoveStatementButton)
        modificationsButtonsWidgetLayout.addWidget(modificationsAddStatementButton)

        self.modificationValuesAreaWidgetLayout.addWidget(modificationsButtonsWidget)

        modificationsPaneLayout.addWidget(QtWidgets.QLabel('Modifications: '), 0, 0, 1, 1)
        modificationsPaneLayout.addWidget(self.modificationValuesArea, 0, 0, 2, 2)

        self.queryTabbedPane.addTab(modificationsPane, 'Modifications')
        ####

        self.entityDropdownTriplets = []

        self.historyTable = QtWidgets.QTableWidget(0, 7, self)
        self.historyTable.setSelectionBehavior(self.historyTable.SelectionBehavior.SelectRows)
        self.historyTable.setSelectionMode(self.historyTable.SelectionMode.SingleSelection)
        self.historyTable.setAcceptDrops(False)
        self.historyTable.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.historyTable.verticalHeader().setCascadingSectionResizes(True)
        self.historyTable.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.historyTable.setHorizontalHeaderLabels(['Query UID', 'Select Clause', 'Select Value(s)', 'Source Clause',
                                                     'Source Value(s)', 'Condition Clause(s)', 'Modification Values'])
        self.queryNewOrHistory.addTab(self.historyTable, 'History')

        self.updateValues()
        self.resize(1000, 600)

    def sourceModeSwitch(self, newText: str):
        if newText == 'FROMDB':
            self.sourceValuesArea.setEnabled(False)
            self.sourceValuesArea.setDisabled(True)
            self.sourceValuesArea.setHidden(True)
        else:
            self.sourceValuesArea.setEnabled(True)
            self.sourceValuesArea.setDisabled(False)
            self.sourceValuesArea.setHidden(False)

    def addSourceClause(self):

        clauseWidget = QtWidgets.QFrame()
        clauseWidgetLayout = QtWidgets.QVBoxLayout()
        clauseWidget.setLayout(clauseWidgetLayout)
        clauseWidget.setFrameStyle(QtWidgets.QFrame.Shape.Panel | QtWidgets.QFrame.Shadow.Raised)
        clauseWidget.setLineWidth(3)

        andOrClause = QtWidgets.QComboBox()
        andOrClause.addItems(['OR', 'AND'])
        specifier = QtWidgets.QComboBox()
        specifier.addItems(['CANVAS', 'RCANVAS'])
        negation = QtWidgets.QComboBox()
        negation.addItems(['MATCHES', 'DOES NOT MATCH'])
        inputDropdown = QtWidgets.QListWidget()
        inputDropdown.setSortingEnabled(True)
        inputDropdown.setSelectionMode(QtWidgets.QListWidget.SelectionMode.SingleSelection)
        inputDropdown.setMinimumHeight(125)
        inputDropdown.addItems(self.mainWindowObject.LQLWIZARD.allCanvases)
        inputText = QtWidgets.QLineEdit('')
        inputText.setFixedHeight(26)
        inputWidget = QtWidgets.QWidget()
        inputWidgetLayout = QtWidgets.QStackedLayout()
        inputWidget.setLayout(inputWidgetLayout)
        inputWidgetLayout.addWidget(inputDropdown)
        inputWidgetLayout.addWidget(inputText)
        specifier.currentIndexChanged.connect(lambda newIndex: inputWidgetLayout.setCurrentIndex(newIndex))

        clauseWidgetLayout.addWidget(andOrClause)
        clauseWidgetLayout.addWidget(specifier)
        clauseWidgetLayout.addWidget(negation)
        clauseWidgetLayout.addWidget(inputWidget)

        if self.sourceValuesAreaWidgetLayout.count() == 1:
            andOrClause.setDisabled(True)
            andOrClause.setToolTip('Cannot edit the set modifier of the first source clause.')

        self.sourceValues.append(clauseWidget)
        self.sourceValuesAreaWidgetLayout.insertWidget(self.sourceValuesAreaWidgetLayout.count() - 1, clauseWidget)

    def removeSourceClause(self):
        if self.sourceValuesAreaWidgetLayout.count() != 1:
            # Remove clause that was added last.
            itemToDel = self.sourceValuesAreaWidgetLayout.takeAt(self.sourceValuesAreaWidgetLayout.count() - 2)
            itemToDel.widget().deleteLater()
            widgetToDel = self.sourceValues.pop()
            widgetToDel.deleteLater()

    def addConditionClause(self):

        clauseWidget = ConditionClauseWidget(self)

        if self.conditionValuesAreaWidgetLayout.count() == 1:
            clauseWidget.andOrClause.setDisabled(True)
            clauseWidget.andOrClause.setToolTip('Cannot edit the set modifier of the first condition clause.')
        self.conditionValues.append(clauseWidget)
        self.conditionValuesAreaWidgetLayout.insertWidget(self.conditionValuesAreaWidgetLayout.count() - 1,
                                                          clauseWidget)

    def removeConditionClause(self):
        if self.conditionValuesAreaWidgetLayout.count() != 1:
            # Remove clause that was added last.
            itemToDel = self.conditionValuesAreaWidgetLayout.takeAt(self.conditionValuesAreaWidgetLayout.count() - 2)
            itemToDel.widget().deleteLater()
            widgetToDel = self.conditionValues.pop()
            widgetToDel.deleteLater()

    def addModificationClause(self):

        clauseWidget = QtWidgets.QFrame()
        clauseWidgetLayout = QtWidgets.QVBoxLayout()
        clauseWidget.setLayout(clauseWidgetLayout)
        clauseWidget.setFrameStyle(QtWidgets.QFrame.Shape.Panel | QtWidgets.QFrame.Shadow.Raised)
        clauseWidget.setLineWidth(3)

        andOrClause = QtWidgets.QLabel('AND')
        specifier = QtWidgets.QComboBox()
        specifier.addItems(['MODIFY', 'RMODIFY'])

        modifyOption = QtWidgets.QComboBox()
        modifyOption.addItems(['NUMIFY', 'UPPERCASE', 'LOWERCASE'])

        inputWidget = QtWidgets.QWidget()
        inputWidgetLayout = QtWidgets.QStackedLayout()

        inputDropdown = QtWidgets.QListWidget()
        inputDropdown.setSortingEnabled(True)
        inputDropdown.setSelectionMode(QtWidgets.QListWidget.SelectionMode.SingleSelection)
        inputDropdown.addItems(self.mainWindowObject.LQLWIZARD.allEntityFields)
        inputDropdown.setMinimumHeight(125)
        inputText = QtWidgets.QLineEdit('')
        inputText.setFixedHeight(26)
        inputWidget.setLayout(inputWidgetLayout)
        inputWidgetLayout.addWidget(inputDropdown)
        inputWidgetLayout.addWidget(inputText)
        specifier.currentIndexChanged.connect(lambda newIndex: inputWidgetLayout.setCurrentIndex(newIndex))

        clauseWidgetLayout.addWidget(andOrClause)
        clauseWidgetLayout.addWidget(specifier)
        clauseWidgetLayout.addWidget(inputWidget)
        clauseWidgetLayout.addWidget(modifyOption)

        if self.modificationValuesAreaWidgetLayout.count() == 1:
            andOrClause.setDisabled(True)
            andOrClause.setToolTip('Cannot edit the set modifier of the first source clause.')
        self.modificationValues.append(clauseWidget)
        self.modificationValuesAreaWidgetLayout.insertWidget(self.modificationValuesAreaWidgetLayout.count() - 1,
                                                             clauseWidget)

    def removeModificationClause(self):
        if self.modificationValuesAreaWidgetLayout.count() != 1:
            # Remove clause that was added last.
            itemToDel = self.modificationValuesAreaWidgetLayout.takeAt(
                self.modificationValuesAreaWidgetLayout.count() - 2)
            itemToDel.widget().deleteLater()
            widgetToDel = self.modificationValues.pop()
            widgetToDel.deleteLater()

    def updateValues(self):
        self.mainWindowObject.LQLWIZARD.takeSnapshot()

        self.selectStatementList.clear()
        self.selectStatementList.addItems(self.mainWindowObject.LQLWIZARD.allEntityFields)
        self.selectStatementTextbox.setText('')

        for _ in range(len(self.sourceValues)):
            widgetToDel = self.sourceValues.pop()
            widgetToDel.deleteLater()

        for _ in range(self.sourceValuesAreaWidgetLayout.count() - 1):
            itemToDel = self.sourceValuesAreaWidgetLayout.takeAt(0)
            itemToDel.widget().deleteLater()

        for _ in range(len(self.conditionValues)):
            widgetToDel = self.conditionValues.pop()
            widgetToDel.deleteLater()

        for _ in range(self.conditionValuesAreaWidgetLayout.count() - 1):
            itemToDel = self.conditionValuesAreaWidgetLayout.takeAt(0)
            itemToDel.widget().deleteLater()

        for _ in range(self.modificationValuesAreaWidgetLayout.count() - 1):
            itemToDel = self.modificationValuesAreaWidgetLayout.takeAt(0)
            itemToDel.widget().deleteLater()

        for _ in range(len(self.modificationValues)):
            widgetToDel = self.modificationValues.pop()
            widgetToDel.deleteLater()

        self.entityDropdownTriplets.clear()
        for entityUID in self.mainWindowObject.LQLWIZARD.databaseSnapshot.nodes:
            nodeDetails = self.mainWindowObject.LQLWIZARD.databaseSnapshot.nodes[entityUID]
            pixmapIcon = QtGui.QPixmap()
            pixmapIcon.loadFromData(nodeDetails['Icon'])
            self.entityDropdownTriplets.append((nodeDetails[list(nodeDetails)[1]], entityUID, pixmapIcon))

        for _ in range(self.historyTable.rowCount()):
            self.historyTable.removeRow(0)

        for oldQueryUID in self.mainWindowObject.LQLWIZARD.QUERIES_HISTORY:
            self.historyTable.insertRow(0)
            self.historyTable.setItem(0, 0, QtWidgets.QTableWidgetItem(str(oldQueryUID)))
            for valueIndex in range(6):
                self.historyTable.setItem(0, valueIndex + 1, QtWidgets.QTableWidgetItem(
                    str(self.mainWindowObject.LQLWIZARD.QUERIES_HISTORY[oldQueryUID][valueIndex])))

    def runQuery(self):
        # Results
        if self.queryNewOrHistory.currentIndex() == 0:
            sourceResults = []
            for sourceValue in self.sourceValues:
                sourceResult = [
                    sourceValue.layout().itemAt(0).widget().currentText(),
                    sourceValue.layout().itemAt(1).widget().currentText(),
                    sourceValue.layout().itemAt(2).widget().currentText()
                    != 'MATCHES',
                ]
                if sourceValue.layout().itemAt(3).widget().layout().currentIndex() == 0:
                    try:
                        sourceResult.append(
                            sourceValue.layout().itemAt(3).widget().layout().itemAt(0).widget().selectedItems()[
                                0].text())
                    except IndexError:
                        continue
                else:
                    sourceResult.append(sourceValue.layout().itemAt(3).widget().layout().itemAt(1).widget().text())
                sourceResults.append(sourceResult)

            conditionResults = []
            for conditionValue in self.conditionValues:
                conditionResult = conditionValue.getValue()
                if conditionResult is not None:
                    conditionResults.append(conditionResult)
            if not conditionResults:
                conditionResults = None

            modificationResults = []
            for modificationValue in self.modificationValues:
                specifierText = modificationValue.layout().itemAt(1).widget().currentText()
                modificationResult = [specifierText]
                if specifierText == 'MODIFY':
                    try:
                        modificationResult.append(
                            modificationValue.layout().itemAt(2).widget().layout().itemAt(0).widget().selectedItems()[
                                0].text())
                    except IndexError:
                        continue
                else:
                    modificationResult.append(
                        modificationValue.layout().itemAt(2).widget().layout().itemAt(1).widget().text())
                modificationResult.append(modificationValue.layout().itemAt(3).widget().currentText())
                modificationResults.append(modificationResult)
            if not modificationResults:
                modificationResults = None

            currentSelectStatement = self.selectStatementPicker.currentText()
            if currentSelectStatement == 'SELECT':
                selectedFields = [
                    item.text()
                    for item in self.selectStatementList.selectedItems()
                ]
            else:
                selectedFields = self.selectStatementTextbox.text()
            sourceStatement = self.sourceStatementPicker.currentText()
            sourceListOrNone = None if sourceStatement == 'FROMDB' else sourceResults

            resultsSet, modificationsSet = self.mainWindowObject.LQLWIZARD.parseQuery(self.mainWindowObject,
                                                                                      currentSelectStatement,
                                                                                      selectedFields, sourceStatement,
                                                                                      sourceListOrNone,
                                                                                      conditionResults,
                                                                                      modificationResults)
        else:
            try:
                selectedHistoryUID = self.historyTable.selectedItems()[0].text()
                resultsSet, modificationsSet = self.mainWindowObject.LQLWIZARD.parseQuery(
                    self.mainWindowObject,
                    *self.mainWindowObject.LQLWIZARD.QUERIES_HISTORY[selectedHistoryUID])
            except IndexError:
                self.mainWindowObject.MESSAGEHANDLER.error('No Query selected from history.', popUp=True)
                return

        self.showResults(resultsSet, modificationsSet)

    def showResults(self, resultsSet, modificationsSet):
        if not resultsSet:
            self.mainWindowObject.MESSAGEHANDLER.warning('Query returned no results.', popUp=True)
            return

        numified = modificationsSet[1] if modificationsSet else None
        qResultsViewer = QueryResultsViewer(self.mainWindowObject, self.mainWindowObject.LQLWIZARD.allEntities,
                                            resultsSet[0], resultsSet[1], numified)
        qResultsViewer.exec()


class QueryResultsViewer(QtWidgets.QDialog):

    def __init__(self, mainWindowObject: MainWindow, entitiesDict: dict, selectedUIDs: set, selectedFields: set,
                 numifiedFields: set):
        super(QueryResultsViewer, self).__init__()
        self.mainWindowObject = mainWindowObject
        self.setModal(True)
        self.setWindowTitle('Query Results')
        dialogLayout = QtWidgets.QGridLayout()
        self.setLayout(dialogLayout)
        self.selectedUIDs = selectedUIDs

        self.resultsTabbedPane = QtWidgets.QTabWidget(self)
        dialogLayout.addWidget(self.resultsTabbedPane, 0, 0, 2, 2)

        self.headerFields = list(selectedFields)
        with contextlib.suppress(ValueError):
            self.headerFields.remove('uid')
        self.headerFields.insert(0, 'uid')

        self.resultsTable = QtWidgets.QTableWidget(0, len(self.headerFields), self)
        self.resultsTable.setHorizontalHeaderLabels(self.headerFields)
        self.resultsTable.setAcceptDrops(False)
        self.resultsTable.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.resultsTable.verticalHeader().setCascadingSectionResizes(True)
        for index in range(1, len(self.headerFields)):
            self.resultsTable.horizontalHeader().setSectionResizeMode(index, QtWidgets.QHeaderView.ResizeMode.Stretch)

        for count, uid in enumerate(selectedUIDs):
            self.resultsTable.insertRow(count)
            for index, field in enumerate(self.headerFields):
                self.resultsTable.setItem(count, index, QtWidgets.QTableWidgetItem(
                    str(entitiesDict[uid].get(field, 'None'))))

        self.resultsTabbedPane.addTab(self.resultsTable, 'Table')

        self.charts = {}
        for headerField in self.headerFields[1:]:
            values = {}
            for entity in entitiesDict:
                entityValue = str(entitiesDict[entity].get(headerField))
                if entityValue not in values:
                    values[entityValue] = 1
                else:
                    values[entityValue] += 1

            if not values:
                # Do not make charts if there are no values to make charts out of.
                continue

            fieldChart = QtCharts.QChart()
            chartTitle = f"{headerField} Chart"
            fieldChart.setTitle(chartTitle)
            fieldChart.setTheme(QtCharts.QChart.ChartTheme.ChartThemeBlueCerulean)
            fieldChart.setMargins(QtCore.QMargins(0, 0, 0, 0))
            chartView = QtCharts.QChartView(fieldChart)
            chartView.setRubberBand(QtCharts.QChartView.RubberBand.NoRubberBand)
            chartView.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            fieldChart.setAnimationOptions(QtCharts.QChart.AnimationOption.AllAnimations)
            fieldChart.setAnimationDuration(250)
            fieldChart.legend().setVisible(True)
            fieldChart.legend().setAlignment(QtCore.Qt.AlignmentFlag.AlignBottom)

            self.charts[headerField] = (fieldChart, chartView)
            self.resultsTabbedPane.addTab(chartView, chartTitle)

            barSeries = QtCharts.QBarSeries()
            barSeries.setName(headerField)
            for barValue, value in values.items():
                barSet = QtCharts.QBarSet(barValue)
                barSet.append(value)
                barSeries.append(barSet)

            fieldChart.addSeries(barSeries)

            xAxis = QtCharts.QBarCategoryAxis()
            xAxis.append([headerField])
            fieldChart.addAxis(xAxis, QtCore.Qt.AlignmentFlag.AlignBottom)
            barSeries.attachAxis(xAxis)

            yAxis = QtCharts.QValueAxis()
            yAxis.setRange(0, max(values.values()) + 1)
            yAxis.applyNiceNumbers()
            fieldChart.addAxis(yAxis, QtCore.Qt.AlignmentFlag.AlignLeft)
            barSeries.attachAxis(yAxis)

        if numifiedFields:
            for field in numifiedFields:
                fieldValues = []
                for entity in entitiesDict:
                    try:
                        entityValue = float(entitiesDict[entity].get(field))
                    except TypeError:
                        continue
                    fieldValues.append(entityValue)
                if not fieldValues:
                    continue
                numValues = len(fieldValues)
                maxValue = max(fieldValues)
                minValue = min(fieldValues)
                meanValue = statistics.fmean(fieldValues)
                medianValue = statistics.median(fieldValues)
                modeValue = statistics.mode(fieldValues)
                sumValue = sum(fieldValues)
                rangeValue = maxValue - minValue
                varianceValue = statistics.pvariance(fieldValues)
                standardDeviationValue = statistics.pstdev(fieldValues)

                numifiedFieldWidget = QtWidgets.QWidget()
                numifiedFieldWidgetLayout = QtWidgets.QVBoxLayout()
                numifiedFieldWidget.setLayout(numifiedFieldWidgetLayout)
                fieldLabel = QtWidgets.QLabel(f'Numerical Information for field: {field}')
                numifiedValuesWidget = QtWidgets.QWidget()
                numifiedValuesWidgetLayout = QtWidgets.QFormLayout()
                numifiedValuesWidget.setLayout(numifiedValuesWidgetLayout)

                numifiedValuesWidgetLayout.addRow('Number of Values: ', QtWidgets.QLabel(str(numValues)))
                numifiedValuesWidgetLayout.addRow('Biggest Value: ', QtWidgets.QLabel(str(maxValue)))
                numifiedValuesWidgetLayout.addRow('Smallest Value: ', QtWidgets.QLabel(str(minValue)))
                numifiedValuesWidgetLayout.addRow('Mean Value: ', QtWidgets.QLabel(str(meanValue)))
                numifiedValuesWidgetLayout.addRow('Median Value: ', QtWidgets.QLabel(str(medianValue)))
                numifiedValuesWidgetLayout.addRow('Mode Value: ', QtWidgets.QLabel(str(modeValue)))
                numifiedValuesWidgetLayout.addRow('Sum of Values: ', QtWidgets.QLabel(str(sumValue)))
                numifiedValuesWidgetLayout.addRow('Range of Values: ', QtWidgets.QLabel(str(rangeValue)))
                numifiedValuesWidgetLayout.addRow('Variance of Values: ', QtWidgets.QLabel(str(varianceValue)))
                numifiedValuesWidgetLayout.addRow('Standard Deviation of Values: ',
                                                  QtWidgets.QLabel(str(standardDeviationValue)))

                numifiedFieldWidgetLayout.addWidget(fieldLabel, 0)
                numifiedFieldWidgetLayout.addWidget(numifiedValuesWidget, 1)

                self.resultsTabbedPane.addTab(
                    numifiedFieldWidget, f'{field} Field Values Information'
                )

        closeButton = QtWidgets.QPushButton('Close')
        closeButton.clicked.connect(self.accept)
        exportButton = QtWidgets.QPushButton('Export Table')
        exportButton.clicked.connect(self.exportData)
        selectOnCurrentCanvasButton = QtWidgets.QPushButton('Select Result Entities on Current Canvas')
        selectOnCurrentCanvasButton.clicked.connect(self.selectOnCurrentCanvas)

        dialogLayout.addWidget(closeButton, 3, 0, 1, 1)
        dialogLayout.addWidget(exportButton, 3, 1, 1, 1)
        dialogLayout.addWidget(selectOnCurrentCanvasButton, 4, 0, 1, 2)

    def selectOnCurrentCanvas(self):
        self.mainWindowObject.centralWidget().tabbedPane.getCurrentScene().selectNodesFromList(self.selectedUIDs)
        self.mainWindowObject.MESSAGEHANDLER.info('Query Result Entities Selected Successfully.', popUp=True)

    def exportData(self):
        exportDialog = QtWidgets.QFileDialog()
        exportDialog.setOption(QtWidgets.QFileDialog.Option.DontUseNativeDialog, True)
        exportDialog.setViewMode(QtWidgets.QFileDialog.ViewMode.List)
        exportDialog.setFileMode(QtWidgets.QFileDialog.FileMode.AnyFile)
        exportDialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        exportDialog.setDirectory(str(Path.home()))

        exportExec = exportDialog.exec()
        if not exportExec:
            self.mainWindowObject.setStatus('Export operation cancelled.')
            return False
        fileName = exportDialog.selectedFiles()[0]
        exportFilePath = Path(fileName)
        if not is_path_exists_or_creatable_portable(str(exportFilePath)):
            self.mainWindowObject.MESSAGEHANDLER.error(
                'Invalid export file name or path to save at.', popUp=True, exc_info=False)
            return False

        try:
            with open(exportFilePath, 'w') as fileToWrite:
                csvWriter = csv.writer(fileToWrite, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                csvWriter.writerow(self.headerFields)
                for rowIndex in range(self.resultsTable.rowCount()):
                    currColumnValues = [
                        self.resultsTable.item(rowIndex, columnIndex).text()
                        for columnIndex in range(self.resultsTable.columnCount())
                    ]
                    csvWriter.writerow(currColumnValues)
        except FileNotFoundError:
            self.mainWindowObject.MESSAGEHANDLER.error('Cannot write file into a non-existing parent directory. '
                                                       'Please create the required parent directories and try again.',
                                                       popUp=True, exc_info=False)
            return False

        self.mainWindowObject.MESSAGEHANDLER.info('Table exported successfully.', popUp=True, exc_info=False)
        return True


class ConditionClauseWidget(QtWidgets.QFrame):

    def __init__(self, parentWizard: QueryBuilderWizard):
        super(ConditionClauseWidget, self).__init__()
        clauseWidgetLayout = QtWidgets.QVBoxLayout()
        self.setLayout(clauseWidgetLayout)
        self.setFrameStyle(QtWidgets.QFrame.Shape.Panel | QtWidgets.QFrame.Shadow.Raised)
        self.setLineWidth(3)

        self.andOrClause = QtWidgets.QComboBox()
        self.andOrClause.addItems(['OR', 'AND'])
        self.specifier = QtWidgets.QComboBox()
        self.specifier.addItems(['Value Condition', 'Graph Condition'])
        self.negation = QtWidgets.QComboBox()
        self.negation.addItems(['MATCHES', 'DOES NOT MATCH'])

        inputWidget = QtWidgets.QWidget()
        inputWidgetLayout = QtWidgets.QStackedLayout()
        inputWidget.setLayout(inputWidgetLayout)

        vcWidget = QtWidgets.QFrame()
        vcWidgetLayout = QtWidgets.QVBoxLayout()
        vcWidget.setLayout(vcWidgetLayout)

        valueInputDropdownAttr = QtWidgets.QComboBox()
        valueInputDropdownAttr.addItems(["ATTRIBUTE", "RATTRIBUTE"])
        userInputDropdownAttr = QtWidgets.QLineEdit('')
        userInputDropdownAttr.setFixedHeight(26)
        valueInputDropdownCondition = QtWidgets.QComboBox()
        valueInputDropdownCondition.addItems(["EQ", "CONTAINS", "STARTSWITH", "ENDSWITH", "RMATCH"])
        userInputDropdownCondition = QtWidgets.QLineEdit('')
        userInputDropdownCondition.setFixedHeight(26)

        vcWidgetLayout.addWidget(valueInputDropdownAttr)
        vcWidgetLayout.addWidget(userInputDropdownAttr)
        vcWidgetLayout.addWidget(valueInputDropdownCondition)
        vcWidgetLayout.addWidget(userInputDropdownCondition)

        gcWidget = QtWidgets.QFrame()
        gcWidgetLayout = QtWidgets.QVBoxLayout()
        gcWidget.setLayout(gcWidgetLayout)

        graphDropdownCondition = QtWidgets.QComboBox()
        graphDropdownCondition.addItems(['CHILDOF', 'DESCENDANTOF', 'PARENTOF', 'ANCESTOROF', 'CONNECTEDTO',
                                         'NUMCHILDREN', 'NUMPARENTS', 'NUMANCESTORS', 'NUMDESCENDANTS',
                                         'NUMIFIED_PARENTS_TOTAL', 'NUMIFIED_CHILDREN_TOTAL',
                                         'ISOLATED', 'ISROOT', 'ISLEAF'])
        gcWidgetLayout.addWidget(graphDropdownCondition)

        gcSecondaryInput = QtWidgets.QWidget()
        self.gcSecondaryInputLayout = QtWidgets.QStackedLayout()
        gcSecondaryInput.setLayout(self.gcSecondaryInputLayout)

        graphEntitiesDropdown = QtWidgets.QTreeWidget()
        graphEntitiesDropdown.setHeaderLabels(['Primary Field', 'UID', 'Icon'])
        graphEntitiesDropdown.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        for entityDropdownTriplet in parentWizard.entityDropdownTriplets:
            newItem = QtWidgets.QTreeWidgetItem()
            newItem.setText(0, entityDropdownTriplet[0])
            newItem.setText(1, entityDropdownTriplet[1])
            newItem.setIcon(2, entityDropdownTriplet[2])
            graphEntitiesDropdown.addTopLevelItem(newItem)

        self.gcSecondaryInputLayout.addWidget(graphEntitiesDropdown)

        graphNumComparisonsWidget = QtWidgets.QWidget()
        graphNumComparisonsWidgetLayout = QtWidgets.QHBoxLayout()
        graphNumComparisonsWidget.setLayout(graphNumComparisonsWidgetLayout)

        graphNumComparisonDropdown = QtWidgets.QComboBox()
        graphNumComparisonDropdown.addItems(['<', '<=', '>', '>=', '=='])
        graphNumInput = QtWidgets.QDoubleSpinBox()
        graphNumInput.setMinimum(0)
        graphNumInput.setMaximum(1000000)  # Can be adjusted higher if need be.
        graphNumInput.setValue(0)
        graphNumComparisonsWidgetLayout.addWidget(graphNumComparisonDropdown)
        graphNumComparisonsWidgetLayout.addWidget(graphNumInput)

        self.gcSecondaryInputLayout.addWidget(graphNumComparisonsWidget)

        emptyWidget = QtWidgets.QWidget()
        self.gcSecondaryInputLayout.addWidget(emptyWidget)

        gcWidgetLayout.addWidget(gcSecondaryInput)

        inputWidgetLayout.addWidget(vcWidget)
        inputWidgetLayout.addWidget(gcWidget)
        self.specifier.currentIndexChanged.connect(lambda newIndex: inputWidgetLayout.setCurrentIndex(newIndex))
        graphDropdownCondition.currentIndexChanged.connect(self.determineSecondaryInput)

        clauseWidgetLayout.addWidget(self.andOrClause)
        clauseWidgetLayout.addWidget(self.specifier)
        clauseWidgetLayout.addWidget(self.negation)
        clauseWidgetLayout.addWidget(inputWidget)

    def determineSecondaryInput(self, conditionIndex: int):
        if conditionIndex < 5:
            self.gcSecondaryInputLayout.setCurrentIndex(0)
        elif conditionIndex < 11:
            self.gcSecondaryInputLayout.setCurrentIndex(1)
        else:
            self.gcSecondaryInputLayout.setCurrentIndex(2)

    def getValue(self):
        specifierValue = self.specifier.currentText()
        returnValues = [self.andOrClause.currentText(),
                        specifierValue]
        if self.negation.currentText() == 'MATCHES':
            returnValues.append(False)
        else:
            returnValues.append(True)
        conditionValue = []
        valueConditionLayout = self.layout().itemAt(3).widget().layout().itemAt(0).widget().layout()

        if specifierValue == 'Value Condition':
            conditionValue.extend(
                (
                    valueConditionLayout.itemAt(0).widget().currentText(),
                    valueConditionLayout.itemAt(1).widget().text(),
                    valueConditionLayout.itemAt(2).widget().currentText(),
                    valueConditionLayout.itemAt(3).widget().text(),
                )
            )
        else:
            conditionValue.append(
                self.layout().itemAt(3).widget().layout().itemAt(1).widget().layout().itemAt(0).widget().currentText())
            if self.gcSecondaryInputLayout.currentIndex() == 0:
                try:
                    conditionValue.append(self.gcSecondaryInputLayout.itemAt(0).widget().selectedItems()[0].text(1))
                except IndexError:
                    return None
            elif self.gcSecondaryInputLayout.currentIndex() == 1:
                conditionValue.append(
                    self.gcSecondaryInputLayout.itemAt(1).widget().layout().itemAt(0).widget().currentText())
                conditionValue.append(
                    self.gcSecondaryInputLayout.itemAt(1).widget().layout().itemAt(1).widget().value())

        returnValues.append(conditionValue)

        return returnValues


class MacroDialog(QtWidgets.QDialog):

    def __init__(self, mainWindowObject: MainWindow):
        super(MacroDialog, self).__init__()
        self.mainWindowObject = mainWindowObject
        self.setModal(True)

        self.resolutionList = []
        for category in mainWindowObject.RESOLUTIONMANAGER.getResolutionCategories():
            self.resolutionList.extend(
                f'{category}/{resolution}'
                for resolution in mainWindowObject.RESOLUTIONMANAGER.getResolutionsInCategory(category)
            )
        self.resolutionList.sort()

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        macroLabel = QtWidgets.QLabel("This is a list of all currently configured Macros.\n"
                                      "Click on a Macro to view the Resolutions included in it.")
        macroLabel.setWordWrap(True)
        self.macroTree = MacroTree(self, mainWindowObject)
        self.macroTree.setSelectionMode(self.macroTree.SelectionMode.ExtendedSelection)
        self.macroTree.setSelectionBehavior(self.macroTree.SelectionBehavior.SelectRows)
        self.macroTree.setHeaderLabels(['Macro UID', 'Delete'])
        self.macroTree.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.macroTree.setSortingEnabled(False)
        # Stretch the first column, since it contains the primary field.
        self.macroTree.header().setStretchLastSection(False)
        self.macroTree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)

        buttonsWidget = QtWidgets.QWidget()
        buttonsWidgetLayout = QtWidgets.QHBoxLayout()
        buttonsWidget.setLayout(buttonsWidgetLayout)
        closeButton = QtWidgets.QPushButton('Close')
        closeButton.clicked.connect(self.reject)
        addMacroButton = QtWidgets.QPushButton('Create New Macro')
        addMacroButton.clicked.connect(self.createMacro)
        runSelectedButton = QtWidgets.QPushButton('Run Selected Macros')
        runSelectedButton.clicked.connect(self.accept)
        buttonsWidgetLayout.addWidget(closeButton)
        buttonsWidgetLayout.addWidget(addMacroButton)
        buttonsWidgetLayout.addWidget(runSelectedButton)

        layout.addWidget(macroLabel)
        layout.addWidget(self.macroTree)
        layout.addWidget(buttonsWidget)
        self.updateMacroTree()
        self.setBaseSize(1000, 1000)

    def updateMacroTree(self) -> None:
        self.macroTree.clear()
        with self.mainWindowObject.macrosLock:
            allMacros = self.mainWindowObject.RESOLUTIONMANAGER.macros

            for macro in allMacros:
                newMacro = MacroTreeItem(macro, allMacros[macro])
                self.macroTree.addTopLevelItem(newMacro)
                self.macroTree.setItemWidget(newMacro, 1, newMacro.deleteButton)

    def createMacro(self) -> None:
        createMacroDialog = MacroCreatorDialog(self.resolutionList)
        if createMacroDialog.exec():
            macroResolutionsList = []
            numberOfResolutionsSelected = createMacroDialog.createList.count()
            for itemIndex in range(numberOfResolutionsSelected):
                itemText = createMacroDialog.createList.item(itemIndex).text()
                resolutionCategory, resolutionName = itemText.split('/', 1)
                rParameters = self.mainWindowObject.RESOLUTIONMANAGER.getResolutionParameters(resolutionCategory,
                                                                                              resolutionName)
                if rParameters is None:
                    message = f'Resolution parameters not found for resolution: {resolutionName}'
                    self.mainWindowObject.MESSAGEHANDLER.error(message, popUp=True, exc_info=False)
                    self.mainWindowObject.setStatus(f'{message}, Macro creation aborted.')
                    return

                resolutionParameterValues = self.mainWindowObject.popParameterValuesAndReturnSpecified(resolutionName,
                                                                                                       rParameters)

                if rParameters:
                    parameterSelector = ResolutionParametersSelector(
                        self.mainWindowObject, resolutionName, rParameters,
                        windowTitle=f'[{str(itemIndex + 1)}/{str(numberOfResolutionsSelected)}] Select Parameter '
                                    f'values for Resolution: {resolutionName}')
                    if parameterSelector.exec():
                        resolutionParameterValues.update(parameterSelector.chosenParameters)
                    else:
                        self.mainWindowObject.MESSAGEHANDLER.info('Macro creation aborted.')
                        self.mainWindowObject.setStatus('Macro creation aborted.')
                        return

                macroResolutionsList.append((itemText, resolutionParameterValues))
            self.mainWindowObject.RESOLUTIONMANAGER.createMacro(macroResolutionsList)
            self.updateMacroTree()
            self.mainWindowObject.setStatus('New Macro Created.')
            self.mainWindowObject.MESSAGEHANDLER.info('New Macro Created.')

    def accept(self) -> None:
        super(MacroDialog, self).accept()


class MacroTree(QtWidgets.QTreeWidget):

    def __init__(self, parent, mainWindowObject):
        super(MacroTree, self).__init__(parent=parent)
        self.mainWindowObject = mainWindowObject

    def deleteMacro(self, treeEntry: QtWidgets.QTreeWidgetItem):
        index = self.indexOfTopLevelItem(treeEntry)
        uid = treeEntry.text(0)
        self.mainWindowObject.RESOLUTIONMANAGER.deleteMacro(uid)
        self.takeTopLevelItem(index)


class MacroTreeItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, uid: str, resolutionList: list):
        super(MacroTreeItem, self).__init__()
        self.setText(0, uid)
        self.uid = uid
        self.setFlags(QtCore.Qt.ItemFlag.ItemIsEditable | self.flags())

        self.deleteButton = QtWidgets.QPushButton('X')
        self.deleteButton.clicked.connect(self.removeSelf)

        for resolution in resolutionList:
            resolutionItem = QtWidgets.QTreeWidgetItem()
            resolutionItem.setText(0, f'Resolution: {resolution[0]}')
            self.addChild(resolutionItem)

    def setData(self, column: int, role: int, value: Any):
        if self.treeWidget() is None:
            # Happens during initialization
            super().setData(column, role, value)

        elif self.treeWidget().mainWindowObject.RESOLUTIONMANAGER.renameMacro(self.uid, value):
            super().setData(column, role, value)
            self.uid = value

    def removeSelf(self):
        self.treeWidget().deleteMacro(self)


class MacroCreatorDialog(QtWidgets.QDialog):

    def __init__(self, resolutionsWithCategoriesList: list):
        super(MacroCreatorDialog, self).__init__()
        self.setWindowTitle('Create new Macro')

        self.viewList = QtWidgets.QListWidget()
        for resolution in resolutionsWithCategoriesList:
            viewItem = QtWidgets.QListWidgetItem(resolution)
            self.viewList.addItem(viewItem)
        self.viewList.sortItems()
        self.viewList.setSelectionMode(self.viewList.SelectionMode.ExtendedSelection)

        buttonsAddRemoveWidget = QtWidgets.QWidget()
        buttonsAddRemoveWidgetLayout = QtWidgets.QVBoxLayout()
        buttonAdd = QtWidgets.QPushButton('>')
        buttonAdd.clicked.connect(self.addSelectedToMacro)
        buttonRemove = QtWidgets.QPushButton('<')
        buttonRemove.clicked.connect(self.removeSelectedFromMacro)
        buttonsAddRemoveWidget.setLayout(buttonsAddRemoveWidgetLayout)
        buttonsAddRemoveWidgetLayout.addWidget(buttonAdd)
        buttonsAddRemoveWidgetLayout.addWidget(buttonRemove)
        self.createList = QtWidgets.QListWidget()
        buttonsRearrangeWidget = QtWidgets.QWidget()
        buttonsRearrangeWidgetLayout = QtWidgets.QVBoxLayout()
        buttonsRearrangeWidget.setLayout(buttonsRearrangeWidgetLayout)
        buttonMoveUp = QtWidgets.QPushButton('^')
        buttonMoveUp.clicked.connect(self.shiftSelectedUp)
        buttonMoveDown = QtWidgets.QPushButton('v')
        buttonMoveDown.clicked.connect(self.shiftSelectedDown)
        buttonsRearrangeWidgetLayout.addWidget(buttonMoveUp)
        buttonsRearrangeWidgetLayout.addWidget(buttonMoveDown)
        allResolutionsLabel = QtWidgets.QLabel('All Resolutions')
        allResolutionsLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        selectedResolutionsLabel = QtWidgets.QLabel('Selected Resolutions')
        selectedResolutionsLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        confirmButton = QtWidgets.QPushButton('Confirm')
        confirmButton.clicked.connect(self.accept)
        cancelButton = QtWidgets.QPushButton('Cancel')
        cancelButton.clicked.connect(self.reject)

        macroCreateLayout = QtWidgets.QGridLayout()
        self.setLayout(macroCreateLayout)
        macroCreateLayout.addWidget(self.viewList, 1, 0, 1, 5)
        macroCreateLayout.addWidget(buttonsAddRemoveWidget, 1, 5, 1, 1)
        macroCreateLayout.addWidget(self.createList, 1, 6, 1, 5)
        macroCreateLayout.addWidget(buttonsRearrangeWidget, 1, 11, 1, 1)
        macroCreateLayout.addWidget(allResolutionsLabel, 0, 0, 1, 5)
        macroCreateLayout.addWidget(selectedResolutionsLabel, 0, 6, 1, 5)
        macroCreateLayout.addWidget(cancelButton, 2, 1, 1, 3)
        macroCreateLayout.addWidget(confirmButton, 2, 7, 1, 3)
        self.setBaseSize(1000, 700)

    def addSelectedToMacro(self):
        for selectedItem in self.viewList.selectedItems():
            self.createList.addItem(QtWidgets.QListWidgetItem(selectedItem.text()))

    def removeSelectedFromMacro(self):
        for selectedItem in self.createList.selectedItems():
            self.createList.takeItem(self.createList.row(selectedItem))

    def shiftSelectedUp(self):
        with contextlib.suppress(IndexError):
            selectedItemIndex = self.createList.row(self.createList.selectedItems()[0])
            if selectedItemIndex != 0:
                currentItem = self.createList.takeItem(selectedItemIndex)
                self.createList.insertItem(selectedItemIndex - 1, currentItem)
                currentItem.setSelected(True)

    def shiftSelectedDown(self):
        with contextlib.suppress(IndexError):
            selectedItemIndex = self.createList.row(self.createList.selectedItems()[0])
            currentItem = self.createList.takeItem(selectedItemIndex)
            self.createList.insertItem(selectedItemIndex + 1, currentItem)
            currentItem.setSelected(True)


class FirstTimeUseDialog(QtWidgets.QDialog):

    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        self.setWindowTitle('Welcome to LinkScope!')

        firstTimeLabel = QtWidgets.QLabel(
            '### Greetings and welcome to LinkScope!\n\n**If this is your first time using this software**, we recommend '
            'going through [our introductory blog post](https://accentusoft.com/tutorials/first-steps-with-linkscope-client/) to '
            'get a feel for how the software works, and what you can do with it. [Our YouTube Channel](https://www.youtube.com/channel/UC8h9Vde1OdezdC2cJ1nEUcw) '
            'has a Playlist called "How To in Less than 30 Seconds" that shows you how to perform common and '
            'not-so-common operations within LinkScope.\n\n**First things first**, we recommend you get started by installing '
            'the Module Packs that you need via the **Modules** tab on the top menu bar, and selecting **View Modules Manager**.')
        firstTimeLabel.setTextFormat(QtCore.Qt.TextFormat.MarkdownText)
        firstTimeLabel.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextBrowserInteraction)
        firstTimeLabel.setOpenExternalLinks(True)
        firstTimeLabel.setWordWrap(True)
        firstTimeLabel.setMinimumWidth(435)

        confirmButton = QtWidgets.QPushButton('Confirm')
        confirmButton.clicked.connect(self.accept)

        layout.addWidget(firstTimeLabel)
        layout.addWidget(confirmButton)
        layout.setStretch(0, 100)


class ExtractCyclesThread(QtCore.QThread):
    cyclesSignal = QtCore.Signal(list, str)

    def __init__(self, tempGraph: nx.DiGraph, nodesList: list, canvasName: str):
        super().__init__()
        self.tempGraph = tempGraph
        self.nodesList = nodesList
        self.canvasName = canvasName

    def run(self) -> None:
        allCycles = list(nx.simple_cycles(self.tempGraph))
        if not allCycles:
            self.cyclesSignal.emit([], self.canvasName)

        if self.nodesList:
            startNode = self.nodesList[0]
        else:
            mostCommonDict = {}
            for cycle in allCycles:
                for node in cycle:
                    mostCommonDict[node] = mostCommonDict.get(node, 0) + 1
            try:
                startNode = max(mostCommonDict, key=mostCommonDict.get)
            except ValueError:
                # No cycles exist.
                self.cyclesSignal.emit([set(), []], self.canvasName)
                return

        reorderedCycles = []
        for cycle in allCycles:
            try:
                reorderedCycles.append(cycle[cycle.index(startNode):] + cycle[:cycle.index(startNode)])
            except ValueError:
                reorderedCycles.append(cycle)

        groups = []
        allElements = set()
        for cycle in list(itertools.zip_longest(*reorderedCycles)):
            cycleSet = set()
            for cycleElement in cycle:
                if cycleElement is not None:
                    cycleSet.add(cycleElement)
                    allElements.add(cycleElement)
            if len(cycleSet) > 1:
                groups.append(cycleSet)

        self.cyclesSignal.emit([allElements, groups], self.canvasName)


if __name__ == '__main__':
    # Create a graphical application
    application = QtWidgets.QApplication(sys.argv)
    application.setOrganizationName("AccentuSoft")
    application.setApplicationName("LinkScope Client")
    qdarktheme.setup_theme()
    mainWindow = MainWindow()
    sys.exit(application.exec())
