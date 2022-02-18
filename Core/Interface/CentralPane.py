#!/usr/bin/env python3

import re
import json
import sys
import threading
from typing import Union
from datetime import datetime

import folium
import networkx as nx
from shutil import move
from msgpack import dump, load
from PIL import Image
from PIL.ImageQt import ImageQt
from pathlib import Path
from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtWidgets import QGraphicsPixmapItem
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from PySide6.QtWebEngineWidgets import QWebEngineView
from Core.Interface import Entity, Stylesheets


class WorkspaceWidget(QtWidgets.QWidget):

    def __init__(self,
                 mainWindow,
                 messageHandler,
                 urlManager,
                 entityDB,
                 resourceHandler):
        super(WorkspaceWidget, self).__init__(parent=mainWindow)

        self.mainWindow = mainWindow
        self.entityDB = entityDB

        self.docAndCanvasLayout = QtWidgets.QGridLayout()
        self.setLayout(self.docAndCanvasLayout)

        self.tabbedPane = TabbedPane(self,
                                     messageHandler,
                                     urlManager,
                                     entityDB,
                                     resourceHandler,
                                     mainWindow)

        self.docAndCanvasLayout.addWidget(self.tabbedPane, 0, 1)
        self.docPane = None
        self.docPaneTitleText = "Document Name"
        self.docPaneBodyText = "Document Summary"

    def toggleLayout(self) -> None:
        if self.docAndCanvasLayout.count() == 1:
            self.docPane = DocWorldPane(self, self.entityDB, self.docPaneTitleText, self.docPaneBodyText)
            self.docAndCanvasLayout.addWidget(self.docPane, 0, 0)
        else:
            # Visual Artefacts remain if the docPane is not deleted.
            self.docPane.deleteLater()

    def setDocTitleAndContents(self, title: Union[str, None] = None, content: Union[str, None] = None) -> None:
        self.docPaneTitleText = title if title else "Document Name"
        self.docPaneBodyText = content if content else "Document Summary"
        if self.docAndCanvasLayout.count() == 2:
            self.docPane.documentTitleWidget.setText(title)
            self.docPane.documentSummaryWidget.setPlainText(content)


class TabBar(QtWidgets.QTabBar):

    def __init__(self, parent, messageHandler) -> None:
        super(TabBar, self).__init__(parent)
        self.setParent(parent)
        self.messageHandler = messageHandler

        self.setTabsClosable(True)
        self.setMovable(True)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == QtGui.Qt.LeftButton:
            currIndex = self.currentIndex()
            currName = self.tabText(currIndex)
            currView = self.parent().getViewAtIndex(currIndex)

            renameOrDeleteDialog = RenameOrDeleteTabDialog(currView.synced, currName)
            dialogResult = renameOrDeleteDialog.exec()

            if dialogResult:
                newTabName = renameOrDeleteDialog.newNameTextBox.text()
                delete = renameOrDeleteDialog.deleteCheckbox.isChecked()
            else:
                return

            if delete:
                sceneToClose = self.parent().canvasTabs[currName].scene()
                groupNodes = [item for item in sceneToClose.items() if isinstance(item, Entity.GroupNode)]
                for groupNode in groupNodes:
                    sceneToClose.removeNode(groupNode)
                self.parent().closeTab(currName)
                return

            if newTabName == currName or newTabName == "":
                return
            if self.parent().isCanvasNameAvailable(newTabName):
                self.parent().renameCanvas(currName, newTabName)
                self.setTabText(currIndex, newTabName)
                currView.name = newTabName
            else:
                self.messageHandler.info(
                    "Failed renaming tab: Canvas name already exists.",
                    popUp=True)


class RenameOrDeleteTabDialog(QtWidgets.QDialog):

    def __init__(self, isSynced: bool, currName: str) -> None:
        super(RenameOrDeleteTabDialog, self).__init__()
        self.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)
        self.setModal(True)
        self.setWindowTitle('Rename Or Delete Tab')

        dialogLayout = QtWidgets.QGridLayout()
        self.setLayout(dialogLayout)

        newNameTextLabel = QtWidgets.QLabel('New Name:')
        self.newNameTextBox = QtWidgets.QLineEdit(currName)
        if isSynced:
            self.newNameTextBox.setDisabled(True)
            self.newNameTextBox.setToolTip(
                "Canvas is synced with server. Synced tabs cannot be renamed.")

        deleteLabel = QtWidgets.QLabel('Delete Tab?')
        self.deleteCheckbox = QtWidgets.QCheckBox('')
        self.deleteCheckbox.setChecked(False)

        acceptButton = QtWidgets.QPushButton('Confirm')
        acceptButton.setAutoDefault(True)
        acceptButton.setDefault(True)
        acceptButton.clicked.connect(self.accept)
        cancelButton = QtWidgets.QPushButton('Cancel')
        cancelButton.clicked.connect(self.reject)

        dialogLayout.addWidget(newNameTextLabel, 0, 0, 1, 1)
        dialogLayout.addWidget(self.newNameTextBox, 0, 1, 1, 1)
        dialogLayout.addWidget(deleteLabel, 1, 0, 1, 1)
        dialogLayout.addWidget(self.deleteCheckbox, 1, 1, 1, 1)
        dialogLayout.addWidget(cancelButton, 2, 0, 1, 1)
        dialogLayout.addWidget(acceptButton, 2, 1, 1, 1)


class TabbedPane(QtWidgets.QTabWidget):
    def __init__(self,
                 parent,
                 messageHandler,
                 urlManager,
                 entityDB,
                 resourceHandler,
                 mainWindow):

        super(TabbedPane, self).__init__(parent)
        self.messageHandler = messageHandler
        self.urlManager = urlManager
        self.entityDB = entityDB
        self.resourceHandler = resourceHandler
        self.mainWindow = mainWindow

        self.setAcceptDrops(True)
        self.setTabBar(TabBar(self, messageHandler))
        self.tabCloseRequested.connect(self.hideTab)
        self.setMinimumSize(300, 300)
        self.canvasTabs = {}
        self.syncedTabs = []
        self.nodeCreationThreads = []

    def addCanvas(self, canvasName='New Graph', graph=None, positions=None, a=0, b=0, c=0, d=0) -> bool:
        if not self.isCanvasNameAvailable(canvasName):
            return False
        scene = CanvasScene(self, graph, positions, a, b, c, d, canvasName)
        view = CanvasView(self,
                          scene,
                          canvasName,
                          self.urlManager)

        self.addTab(view, canvasName)
        self.canvasTabs[canvasName] = view

        return True

    def markCanvasAsSyncedByName(self, canvasName: str = None):
        """
        Sync the canvas with the specified name, or the one at the current
        index if no name is specified.
        """
        if canvasName is not None:
            syncIndex = self.getTabIndexByName(canvasName)
        else:
            syncIndex = self.currentIndex()
        syncName = list(self.canvasTabs)[syncIndex]
        if syncName in self.syncedTabs:
            return None, None
        syncView = self.getViewAtIndex(syncIndex)
        syncView.synced = True
        self.setTabIcon(syncIndex,
                        QtGui.QIcon(self.resourceHandler.getIcon("uploading")))
        self.syncedTabs.append(syncName)
        return syncName, self.canvasTabs[syncName].scene().sceneGraph

    def unmarkSyncedCanvasesByName(self, canvasToUnSync: str = None) -> None:
        if canvasToUnSync is not None:
            try:
                self.syncedTabs.remove(canvasToUnSync)
            except ValueError:
                # In case the tab to unSync isn't actually synced.
                pass
            syncIndex = self.getTabIndexByName(canvasToUnSync)
            syncView = self.getViewAtIndex(syncIndex)
            self.setTabIcon(syncIndex, QtGui.QIcon())
            syncView.synced = False
        else:
            for tabName in self.syncedTabs:
                syncIndex = self.getTabIndexByName(tabName)
                syncView = self.getViewAtIndex(syncIndex)
                self.setTabIcon(syncIndex, QtGui.QIcon())
                syncView.synced = False
            self.syncedTabs = []

    def isCanvasNameAvailable(self, canvasName: str) -> bool:
        """
        Checks if the specified canvas name is available.
        """
        if canvasName in self.canvasTabs:
            return False
        return True

    def renameCanvas(self, currName: str, newName: str) -> None:
        self.canvasTabs = {newName if key == currName else
                           key: value for key, value in self.canvasTabs.items()}
        self.canvasTabs[newName].name = newName

    def getViewAtIndex(self, index: int):
        return self.canvasTabs[self.tabText(index)]

    def closeTab(self, tabName: str) -> None:
        for tabIndex in range(self.count()):
            if self.tabText(tabIndex) == tabName:
                self.removeTab(tabIndex)
                break
        self.canvasTabs.pop(tabName)

    def hideTab(self, index) -> None:
        self.removeTab(index)

    def showTab(self, canvasName) -> None:
        if canvasName in self.canvasTabs:
            view = self.canvasTabs[canvasName]
            self.insertTab(list(self.canvasTabs).index(canvasName), view, canvasName)
            if view.synced:
                syncIndex = self.getTabIndexByName(canvasName)
                self.setTabIcon(syncIndex, QtGui.QIcon(self.resourceHandler.getIcon("uploading")))

    def getTabIndexByName(self, tabName):
        count = 0
        for tab in self.canvasTabs:
            if tab == tabName:
                return count
            count += 1
        return None

    def getSceneByName(self, tabName):
        tabView = self.canvasTabs.get(tabName)
        if tabView is not None:
            return tabView.scene()
        return None

    def getNameOfScene(self, scene) -> str:
        for tab in self.canvasTabs:
            if self.canvasTabs[tab].scene() == scene:
                return self.canvasTabs[tab].name

    def createHomeTab(self) -> None:
        if len(self.canvasTabs) == 0:
            self.addCanvas('Home')

    def dragEnterEvent(self, event) -> None:
        event.accept()

    def getCurrentScene(self):
        return self.canvasTabs[self.tabText(self.currentIndex())].scene()

    def getCurrentView(self):
        return self.canvasTabs[self.tabText(self.currentIndex())]

    def disableAllTabsExceptCurrent(self) -> None:
        """
        Useful to stop the user from switching tabs in the middle of
          an operation.
        """
        currIndex = self.currentIndex()
        for tab in range(len(self.canvasTabs)):
            if tab != currIndex:
                self.setTabEnabled(tab, False)
            self.setTabsClosable(False)

    def enableAllTabs(self) -> None:
        """
        Useful when you've disabled all tabs, and want to enable them.
        """
        for tab in range(len(self.canvasTabs)):
            self.setTabEnabled(tab, True)
            self.setTabsClosable(True)

    def facilitateResolution(self, resolution_name: str, resolution_result: list) -> None:
        # fromServer is used to prevent updates from being pushed to server - canvas is synced after
        #   the resolution is done

        # Having a very granular progress bar results in a massive slowdown (i.e. resolutions take 5x< the time).
        steps = 3
        progress = QtWidgets.QProgressDialog('Resolving new nodes for resolution: ' + resolution_name +
                                             ', please wait...', 'Abort Resolving Nodes', 0, steps, self)
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.setMinimumDuration(1500)

        # Get all the entities, then split it into several lists, to make searching & iterating through them faster.
        allEntities = [(entity['uid'], (entity[list(entity)[1]], entity['Entity Type']))
                       for entity in self.entityDB.getAllEntities()]
        # In case we have no entities in the database when the resolution finishes, i.e. the user deletes the origin
        #   node for the resolution, or runs something that creates nodes from nothing.
        if allEntities:
            allEntityUIDs, allEntityPrimaryFieldsAndTypes = map(list, zip(*allEntities))
        else:
            allEntityUIDs = []
            allEntityPrimaryFieldsAndTypes = []
        allLinks = [linkUID['uid'] for linkUID in self.entityDB.getAllLinks()]
        links = []
        newNodeUIDs = []
        for resultList in resolution_result:
            newNodeJSON = resultList[0]
            newNodeEntityType = newNodeJSON.get('Entity Type')
            # Cannot assume proper order of dicts sent over the net.
            newNodePrimaryFieldKey = self.mainWindow.RESOURCEHANDLER.getPrimaryFieldForEntityType(newNodeEntityType)
            newNodePrimaryField = newNodeJSON.get(newNodePrimaryFieldKey)
            if not newNodeEntityType or not newNodePrimaryField:
                continue

            try:
                # Attempt to get the index of an existing entity that shares primary field and type with the new
                #   entity. Those two entities are considered to be referring to the same thing.
                newNodeExistsIndex = allEntityPrimaryFieldsAndTypes.index((newNodePrimaryField, newNodeEntityType))

                # If entity already exists, update the fields and re-add
                newNodeExistingUID = allEntityUIDs[newNodeExistsIndex]
                existingEntityJSON = self.entityDB.getEntity(newNodeExistingUID)
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
                # Remove any 'None' values from new nodes - we want to keep all collected info.
                for potentiallyNoneKey, potentiallyNoneValue in dict(newNodeJSON).items():
                    if potentiallyNoneValue is None or potentiallyNoneValue == 'None':
                        del newNodeJSON[potentiallyNoneKey]
                # Update old values to new ones, and add new ones where applicable.
                existingEntityJSON.update(newNodeJSON)
                self.entityDB.addEntity(existingEntityJSON, fromServer=True, updateTimeline=False)
                newNodeUIDs.append(newNodeExistingUID)
            except ValueError:
                # If there is no index for which the primary field and entity type of the new node match one of the
                #   existing ones, the node must indeed be new. We add it here.
                entityJson = self.entityDB.addEntity(newNodeJSON, fromServer=True, updateTimeline=False)
                newNodeUIDs.append(entityJson['uid'])
                # Ensure that different entities involved in the resolution can't independently
                #   create the same new entities.
                allEntityUIDs.append(entityJson['uid'])
                allEntityPrimaryFieldsAndTypes.append((newNodePrimaryField, newNodeEntityType))

        progress.setValue(1)
        for resultListIndex in range(len(newNodeUIDs)):
            outputEntityUID = newNodeUIDs[resultListIndex]
            parentsDict = resolution_result[resultListIndex][1]
            for parentID in parentsDict:
                parentUID = parentID
                if isinstance(parentUID, int):
                    parentUID = newNodeUIDs[parentUID]
                # Sanity check: Check that the node that was used for this resolution still exists.
                if parentUID in allEntityUIDs:
                    resolutionName = parentsDict[parentID].get('Resolution', 'Link')
                    newLinkUID = (parentUID, outputEntityUID)
                    # Avoid creating more links between the same two entities.
                    if newLinkUID in allLinks:
                        linkJson = self.entityDB.getLinkIfExists(newLinkUID)
                        if resolutionName not in linkJson['Notes']:
                            linkJson['Notes'] += '\nConnection also produced by Resolution: ' + resolutionName
                            self.entityDB.addLink(linkJson, fromServer=True)
                    else:
                        newLink = self.entityDB.addLink({'uid': newLinkUID, 'Resolution': resolutionName,
                                                         'Notes': parentsDict[parentID].get('Notes', '')},
                                                        fromServer=True)
                        if newLink is not None:
                            links.append((parentUID, outputEntityUID, resolutionName))
                            allLinks.append(newLinkUID)

        progress.setValue(2)

        self.mainWindow.syncDatabase()
        self.addLinksToTabs(links, resolution_name)
        progress.setValue(3)
        self.entityDB.resetTimeline()
        self.mainWindow.saveProject()
        self.mainWindow.MESSAGEHANDLER.info('Resolution ' + resolution_name + ' completed successfully.')

    def linkAddHelper(self, links) -> None:
        """
        Add a list of links in the database.
        Overwrites existing links, if they have the same uid.

        :param links:
        :return:
        """
        newLinks = []

        for link in links:
            linkUID = (link[0], link[1])
            lJson = self.entityDB.getLinkIfExists(linkUID)
            if lJson is None:
                self.entityDB.addLink({'uid': linkUID, 'Resolution': link[2], 'Notes': link[3]})
            newLinks.append((link[0], link[1], link[2]))

        self.addLinksToTabs(newLinks)
        self.entityDB.resetTimeline()

    def addLinksToTabs(self, newLinks, resolution_name: str = 'Entity Group',
                       linkGroupingOverride: bool = False) -> None:
        for canvas in self.canvasTabs:
            scene = self.canvasTabs[canvas].scene()
            sceneChanged = False
            with scene.resolutionThreadingLock:
                addedNodes = []

                for newLink in newLinks:
                    uid = newLink[1]
                    parentUID = newLink[0]
                    if parentUID in scene.nodesDict and uid not in scene.nodesDict:
                        sceneChanged = True

                        nodeJSON = self.entityDB.getEntity(uid)

                        # This is more efficient for large canvases than syncing afterwards.
                        self.mainWindow.sendLocalCanvasUpdateToServer(canvas, uid)

                        picture = nodeJSON.get('Icon')
                        scene.sceneGraph.add_node(uid)

                        try:
                            nodePrimaryAttribute = nodeJSON.get(list(nodeJSON)[1])
                        except IndexError:
                            nodePrimaryAttribute = ''
                        newNode = Entity.BaseNode(picture, uid, nodePrimaryAttribute)
                        scene.addNodeToScene(newNode)
                        scene.addLinkDragDrop(scene.nodesDict[parentUID], newNode, newLink[2])

                        addedNodes.append(newNode)
                    elif parentUID in scene.nodesDict and uid in scene.nodesDict:
                        # Need to send this to server, since it won't be drawn otherwise.
                        scene.addLinkDragDrop(scene.nodesDict[parentUID], scene.nodesDict[uid], newLink[2])

                if len(addedNodes) >= int(self.mainWindow.SETTINGS.value(
                        "Project/Resolution Result Grouping Threshold", "15")) and not linkGroupingOverride:
                    itemUIDs = [item.uid for item in addedNodes]
                    newGroupEntity = self.parent().entityDB.addEntity(
                        {'Group Name': resolution_name,
                         'Child UIDs': itemUIDs, 'Entity Type': 'EntityGroup'})
                    uid = newGroupEntity['uid']

                    [scene.removeNode(item) for item in addedNodes]
                    scene.addNodeProgrammatic(uid, itemUIDs, fromServer=True)

            if sceneChanged:
                scene.rearrangeGraph()
                # self.mainWindow.syncCanvasByName(canvas)

    def serverLinkAddHelper(self, linkJson: dict, overwrite: bool = False) -> None:
        """
        Assumes that the 'uid' field is a tuple.

        :param overwrite:
        :param linkJson:
        :return:
        """
        linkUID = linkJson['uid']
        lJson = self.entityDB.addLink(linkJson, fromServer=True, overwrite=overwrite)
        if lJson is not None:
            for canvas in self.canvasTabs:
                if self.canvasTabs[canvas].scene().sceneGraph.nodes.get(linkUID[0]) is not None:
                    if self.canvasTabs[canvas].scene().sceneGraph.nodes.get(linkUID[1]) is None:
                        self.canvasTabs[canvas].scene().addNodeProgrammatic(linkUID[1], fromServer=True)
                    elif self.canvasTabs[canvas].scene().sceneGraph.edges.get(linkUID) is None:
                        self.canvasTabs[canvas].scene().addLinkProgrammatic(linkUID, lJson['Resolution'],
                                                                            fromServer=True)
                    self.canvasTabs[canvas].scene().rearrangeGraph()

    def nodeRemoveAllHelper(self, nodeUID: str) -> None:
        for canvas in self.canvasTabs:
            currentScene = self.canvasTabs[canvas].scene()
            if nodeUID in currentScene.nodesDict:
                currentScene.removeNode(currentScene.nodesDict[nodeUID])

    def linkRemoveAllHelper(self, linkUID) -> None:
        for canvas in self.canvasTabs:
            currentScene = self.canvasTabs[canvas].scene()
            currentScene.removeUIDFromLink(linkUID)

    def save(self) -> None:
        if len(self.canvasTabs) == 0:
            return
        canvasDBPath = Path(self.mainWindow.SETTINGS.value("Project/BaseDir")) / "Project Files" / "canvasTabs.lscanvas"
        canvasDBPathTmp = canvasDBPath.with_suffix(canvasDBPath.suffix + '.tmp')

        canvasDBFile = open(canvasDBPathTmp, "wb")
        saveJson = {}
        for canvasName in self.canvasTabs:
            saveJson[canvasName] = [
                self.resourceHandler.deconstructGraphForFileDump(self.canvasTabs[canvasName].scene().sceneGraph),
                self.canvasTabs[canvasName].scene().scenePos]
        dump(saveJson, canvasDBFile)
        canvasDBFile.close()
        move(canvasDBPathTmp, canvasDBPath)

    def open(self) -> None:
        canvasDBPath = Path(self.mainWindow.SETTINGS.value("Project/BaseDir")) / "Project Files" / "canvasTabs.lscanvas"

        if Path(canvasDBPath).exists():
            try:
                canvasDBFile = open(canvasDBPath, "rb")
                savedJson = load(canvasDBFile)
                for canvasName in savedJson:
                    self.addCanvas(canvasName,
                                   self.resourceHandler.reconstructGraphFullFromFile(savedJson[canvasName][0]),
                                   savedJson[canvasName][1])
                canvasDBFile.close()
            except Exception as exc:
                self.messageHandler.error("Exception occurred when opening tabs: " + str(exc) +
                                          "\nSkipping opening tabs.", popUp=True)


class DocWorldPane(QtWidgets.QWidget):

    def __init__(self, parent: QtWidgets.QWidget, entityDB, documentTitleText: str, documentSummaryText: str) -> None:
        super(DocWorldPane, self).__init__(parent)
        self.entityDB = entityDB
        self.setLayout(QtWidgets.QVBoxLayout())
        self.setFixedWidth(425)

        self.documentTitleWidget = QtWidgets.QLabel(documentTitleText)
        self.documentSummaryWidget = QtWidgets.QPlainTextEdit(documentSummaryText)
        self.documentSummaryWidget.setReadOnly(True)

        self.layout().addWidget(self.documentTitleWidget)
        self.layout().addWidget(self.documentSummaryWidget)
        getSummaryButton = QtWidgets.QPushButton('Get Summary of Selected Document')
        getSummaryButton.clicked.connect(self.getDocumentSummary)
        self.layout().addWidget(getSummaryButton)

        self.m = folium.Map(location=[0, 0], zoom_start=2)
        mapTitle = QtWidgets.QLabel("Location Map")
        showMapButton = QtWidgets.QPushButton('Show Map')
        showMapButton.clicked.connect(self.showMap)
        self.layout().addWidget(mapTitle)
        self.layout().addWidget(showMapButton)

    def getDocumentSummary(self):
        self.parent().mainWindow.getSummaryOfDocument(None)

    def showMap(self) -> None:
        self.resetMap()
        markerEntities = [entity for entity in self.entityDB.getAllEntities()
                          if entity.get('Latitude') is not None and
                          entity.get('Longitude') is not None]
        for marker in markerEntities:
            coordinates = [float(marker['Latitude'].replace(',', '.')),
                           float(marker['Longitude'].replace(',', '.'))]
            label = marker[list(marker)[1]]
            self.addMarker(coordinates, label)
        html = self.m.get_root().render()
        geoMap = QWebEngineView()

        geoMap.setHtml(html, QtCore.QUrl('http://openstreetmap.org'))
        # geoMap.reload()
        WordMapDialog(geoMap).exec_()

    def addMarker(self, coordinates: list, name: str = '') -> None:
        folium.Marker(location=coordinates, popup=name).add_to(self.m)

    def resetMap(self) -> None:
        self.m = folium.Map(location=[0, 0], zoom_start=2)


class WordMapDialog(QtWidgets.QDialog):

    def __init__(self, mapWidget: QWebEngineView) -> None:
        super(WordMapDialog, self).__init__()
        self.setWindowTitle('World Map')

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(mapWidget)
        self.show()


# Pan and zoom: https://stackoverflow.com/questions/35508711/how-to-enable-pan-and-zoom-in-a-qgraphicsview
class CanvasView(QtWidgets.QGraphicsView):

    def __init__(self, parent, scene, name, urlManager) -> None:
        self.tabbedPane = parent
        super(CanvasView, self).__init__(parent=parent)

        self.zoom = 0
        self.setScene(scene)
        self.name = name
        self.urlManager = urlManager

        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        # self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        # self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(54, 69, 79)))
        self.setFrameShape(QtWidgets.QFrame.NoFrame)

        self.setAcceptDrops(True)
        self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))

        self.dragOver = False
        self.synced = False

        self.menu = QtWidgets.QMenu()
        self.menu.setStyleSheet(Stylesheets.MENUS_STYLESHEET_2)
        viewMenu = self.menu.addMenu("Hide / Delete")
        viewMenu.setStyleSheet(Stylesheets.MENUS_STYLESHEET_2)
        groupingMenu = self.menu.addMenu("Grouping")
        groupingMenu.setStyleSheet(Stylesheets.MENUS_STYLESHEET_2)

        actionDelete = QtGui.QAction('Hide Selected Items',
                                     viewMenu,
                                     statusTip="Hide selected items from this canvas.",
                                     triggered=self.scene().deleteSelectedItems)
        viewMenu.addAction(actionDelete)

        actionDeleteFromDatabase = QtGui.QAction('Delete Selected Items',
                                                 viewMenu,
                                                 statusTip="Delete selected items from this project.",
                                                 triggered=self.deleteItemsFromDatabase)
        viewMenu.addAction(actionDeleteFromDatabase)

        self.actionLinkDelete = QtGui.QAction('Delete Selected Links',
                                              viewMenu,
                                              statusTip="Delete selected links from this canvas.",
                                              triggered=self.deleteSelectedLinks)
        viewMenu.addAction(self.actionLinkDelete)

        self.actionGroup = QtGui.QAction('Group Selected Entities',
                                         groupingMenu,
                                         statusTip="Group together selected entity items into one entity.",
                                         triggered=self.groupSelectedItems)
        groupingMenu.addAction(self.actionGroup)

        self.actionUngroup = QtGui.QAction('Ungroup Selected Entities',
                                           groupingMenu,
                                           statusTip="Ungroup selected group entity items.",
                                           triggered=self.ungroupSelectedItems)
        groupingMenu.addAction(self.actionUngroup)

        self.actionAddGroup = QtGui.QAction('Add Selected Entities to Existing Group',
                                            groupingMenu,
                                            statusTip="Add selected entities to an existing group entity.",
                                            triggered=self.appendSelectedItemsToGroup)
        groupingMenu.addAction(self.actionAddGroup)

        entitiesToOtherCanvasAction = QtGui.QAction('Send Selected Entities to Other Canvas',
                                                    self.menu,
                                                    statusTip="Send the selected entities to a different, existing "
                                                              "canvas.",
                                                    triggered=self.sendEntitiesToOtherCanvas)
        self.menu.addAction(entitiesToOtherCanvasAction)

        importConnectedEntitiesAction = QtGui.QAction('Import Connected Entities',
                                                      self.menu,
                                                      statusTip="Import all entities directly connected to the "
                                                                "selected entities (both incoming and outgoing), into "
                                                                "this canvas.",
                                                      triggered=self.importConnectedEntities)
        self.menu.addAction(importConnectedEntitiesAction)

    def deleteItemsFromDatabase(self) -> None:
        items = self.scene().selectedItems()
        for item in items:
            if isinstance(item, Entity.BaseNode):
                if isinstance(item, Entity.GroupNode):
                    for childUID in list(item.groupedNodesUid):
                        self.tabbedPane.nodeRemoveAllHelper(childUID)
                        self.tabbedPane.mainWindow.LENTDB.removeEntity(childUID, updateTimeLine=False)
                self.tabbedPane.nodeRemoveAllHelper(item.uid)
                self.tabbedPane.mainWindow.LENTDB.removeEntity(item.uid, updateTimeLine=False)
        self.tabbedPane.mainWindow.LENTDB.resetTimeline()

    def adjustSceneRect(self) -> None:
        self.scene().adjustSceneRect()

    def drawBackground(self, painter: QtGui.QPainter, rect: Union[QtCore.QRectF, QtCore.QRect]) -> None:
        super(CanvasView, self).drawBackground(painter, rect)
        # Ensure that all links will always be drawn.
        [link.paint(painter, None, None) for link in list(self.scene().linksDict.values())]

    def centerViewportOnNode(self, uid: str) -> None:
        node = self.scene().getVisibleNodeForUID(uid)
        if node is not None:
            self.centerOn(node)

    def dragMoveEvent(self, event) -> None:
        itemsMoved = self.scene().selectedItems()
        if len(itemsMoved) != 0:
            self.ensureVisible(itemsMoved[0], 50, 50)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasText() or event.mimeData().hasImage():
            event.setAccepted(True)
            self.dragOver = True
            self.update()

    def dragLeaveEvent(self, event) -> None:
        pass

    def dropEvent(self, event) -> None:
        pos = self.mapToScene(event.pos())
        self.dragOver = False
        mimeData = event.mimeData()
        jsonData = None

        # Ref: https://doc.qt.io/qtforpython/PySide6/QtCore/QMimeData.html
        if mimeData.hasUrls():
            jsonData = self.urlManager.handleURLs(mimeData.urls())
        elif mimeData.hasText():
            try:
                jsonData = [json.loads(mimeData.text())]
            except json.decoder.JSONDecodeError:
                # Import as a Phrase entity
                jsonData = [{'Phrase': mimeData.text(), 'Entity Type': 'Phrase'}]

        if jsonData is None:
            return

        # If a single node is dropped in
        if len(jsonData) == 1:
            nodeJson = jsonData[0]
            if nodeJson is not None:
                entityJson = None
                if nodeJson.get('uid') is not None:
                    entityJson = self.tabbedPane.entityDB.getEntity(nodeJson.get('uid'))

                # If a new node is dropped in (i.e. does not already exist in the database)
                if entityJson is None:
                    entityJson = self.tabbedPane.entityDB.addEntity(nodeJson)
                entityUID = entityJson['uid']

                if entityUID not in self.scene().sceneGraph.nodes():
                    if entityJson['Entity Type'] == 'EntityGroup':
                        newGroup = self.tabbedPane.mainWindow.copyGroupEntity(entityUID, self.scene())
                        if newGroup is not None:
                            newNode = self.scene().addNodeProgrammatic(newGroup['uid'], newGroup['Child UIDs'])
                            newNode.setPos(pos.x() - 20, pos.y() - 20)
                        else:
                            self.tabbedPane.messageHandler.warning("Cannot add selected Group Node to scene: Scene "
                                                                   "already contains all nodes that the Group Node "
                                                                   "currently contains.", popUp=True)
                    else:
                        self.scene().addNodeDragDrop(
                            entityUID,
                            pos.x() - 20,
                            pos.y() - 20)
                else:
                    wasGrouped = False
                    for groupNode in [node for node in self.items() if isinstance(node, Entity.GroupNode)]:
                        wasGrouped = \
                            groupNode.removeSpecificItemFromGroupIfExists(entityUID)
                        if wasGrouped:
                            self.removeGroupNodeLinksForUID(groupNode.uid, entityUID)
                            groupNodeJson = self.tabbedPane.entityDB.getEntity(groupNode.uid)
                            groupNodeJson['Child UIDs'].remove(entityUID)
                            self.tabbedPane.entityDB.addEntity(groupNodeJson)
                            self.scene().addNodeDragDrop(entityUID,
                                                         pos.x() - 20,
                                                         pos.y() - 20
                                                         )
                            break
                    if not wasGrouped:
                        for item in self.scene().items():
                            if not isinstance(item, Entity.BaseNode):
                                continue
                            if item.uid == entityUID:
                                item.setPos(QtCore.QPointF(pos.x() - 20, pos.y() - 20))
                                self.scene().updatePositionInDB(
                                    entityUID,
                                    pos.x() - 20,
                                    pos.y() - 20
                                )
                                break
                if len(nodeJson) > 1:
                    primaryField = self.tabbedPane.resourceHandler.getPrimaryFieldForEntityType(
                        entityJson['Entity Type'])
                    defaultJSON = self.tabbedPane.resourceHandler.getBareBonesEntityJson(entityJson['Entity Type'])
                    if defaultJSON[primaryField] == entityJson[primaryField]:
                        self.scene().editEntityProperties(entityJson['uid'])

        # If multiple nodes are dropped in
        else:
            for nodeJson in jsonData:
                if nodeJson is None:
                    continue
                entityJson = None
                if nodeJson.get('uid') is not None:
                    entityJson = self.tabbedPane.entityDB.getEntity(nodeJson.get('uid'))
                if entityJson is None:
                    entityJson = self.tabbedPane.entityDB.addEntity(nodeJson)
                if entityJson['uid'] not in self.scene().sceneGraph.nodes():
                    self.scene().addNodeProgrammatic(entityJson['uid'])
            self.scene().rearrangeGraph()

    def cleanDeletedNodeFromGroupsIfExists(self, entityUID) -> None:
        # Entities are unique - only one instance exists in each canvas.
        # This should search all group nodes, regardless of whether they are nested or not.
        for groupNode in [node for node in self.items() if isinstance(node, Entity.GroupNode)]:
            wasGrouped = \
                groupNode.removeSpecificItemFromGroupIfExists(entityUID)
            if wasGrouped:
                self.removeGroupNodeLinksForUID(groupNode.uid, entityUID)

                # Should not be needed.
                groupNodeJson = self.tabbedPane.entityDB.getEntity(groupNode.uid)
                if groupNodeJson is not None:
                    if entityUID in groupNodeJson['Child UIDs']:
                        groupNodeJson['Child UIDs'].remove(entityUID)
                    self.tabbedPane.entityDB.addEntity(groupNodeJson)

                break
        try:
            self.scene().sceneGraph.remove_node(entityUID)
        except nx.exception.NetworkXError:
            # Node is already removed
            pass

    def removeGroupNodeLinksForUID(self, groupUID, nodeUID) -> None:
        self.scene().removeGroupNodeLinksForUID(groupUID, nodeUID)

    def mouseReleaseEvent(self, event) -> None:
        QtWidgets.QGraphicsView.mouseReleaseEvent(self, event)
        self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        itemsMoved = [item for item in self.scene().selectedItems()
                      if isinstance(item, Entity.BaseNode)]
        for item in itemsMoved:
            self.scene().updatePositionInDB(item.uid,
                                            item.pos().x(),
                                            item.pos().y())
        self.adjustSceneRect()

    def wheelEvent(self, event) -> None:
        if len(self.scene().items()) > 0:
            if event.angleDelta().y() > 0:
                if self.zoom == 0:
                    return
                factor = 1.25
                self.zoom += 1
            else:
                # Prevent user from zooming out indefinitely.
                if self.zoom < -10:
                    return
                factor = 0.8
                self.zoom -= 1
            self.scale(factor, factor)

    def mousePressEvent(self, event) -> None:
        if event.button() == QtCore.Qt.MouseButton.RightButton and \
                not self.scene().linking and not self.scene().appendingToGroup:
            if len(self.scene().selectedItems()) == 0:
                self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
            else:
                items = self.scene().selectedItems()
                groupItems = [groupItem for groupItem in items if isinstance(groupItem, Entity.GroupNode)]
                linkItems = [linkItem for linkItem in items if isinstance(linkItem, Entity.BaseConnector)]
                if len(groupItems) > 0:
                    self.actionUngroup.setDisabled(False)
                    self.actionUngroup.setEnabled(True)
                else:
                    self.actionUngroup.setDisabled(True)
                    self.actionUngroup.setEnabled(False)
                if len(items) > 1:
                    self.actionGroup.setDisabled(False)
                    self.actionGroup.setEnabled(True)
                else:
                    self.actionGroup.setDisabled(True)
                    self.actionGroup.setEnabled(False)
                if len(linkItems) > 0:
                    self.actionLinkDelete.setDisabled(False)
                    self.actionLinkDelete.setEnabled(True)
                else:
                    self.actionLinkDelete.setDisabled(True)
                    self.actionLinkDelete.setEnabled(False)

                self.menu.exec(QtGui.QCursor.pos())
        elif event.button() == QtCore.Qt.MouseButton.RightButton and self.scene().appendingToGroup:
            self.scene().appendSelectedItemsToGroupToggle()
        elif event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        super(CanvasView, self).mousePressEvent(event)

    def deleteSelectedLinks(self) -> None:
        linkUIDs = []
        [linkUIDs.append(item.uid) for item in self.scene().selectedItems() if isinstance(item, Entity.BaseConnector)]
        for linkUID in linkUIDs:
            self.tabbedPane.mainWindow.deleteSpecificLink(linkUID)

    def groupSelectedItems(self) -> None:
        self.scene().groupSelectedItems()
        self.adjustSceneRect()

    def ungroupSelectedItems(self) -> None:
        self.scene().ungroupSelectedItems()
        self.adjustSceneRect()

    def appendSelectedItemsToGroup(self) -> None:
        self.scene().appendSelectedItemsToGroupToggle()
        self.adjustSceneRect()

    def sendEntitiesToOtherCanvas(self) -> None:
        entitiesToSend = [item.uid for item in self.scene().selectedItems()
                          if isinstance(item, Entity.BaseNode) and not isinstance(item, Entity.GroupNode)]
        groupEntitiesToSend = [item.uid for item in self.scene().selectedItems()
                               if isinstance(item, Entity.GroupNode)]

        otherTabs = [tabName for tabName in self.tabbedPane.canvasTabs if tabName != self.name]
        prompt = SendToOtherTabCanvasSelector(otherTabs)

        if prompt.exec():
            otherCanvasName = prompt.canvasNameSelector.currentText()
            if otherCanvasName:
                otherCanvas = self.tabbedPane.canvasTabs[otherCanvasName].scene()
                for entityToSend in entitiesToSend:
                    if otherCanvas.sceneGraph.nodes.get(entityToSend) is None:
                        otherCanvas.addNodeProgrammatic(entityToSend)
                for groupEntityToSend in groupEntitiesToSend:
                    # Have to make a new group entity, so that ungrouping in one canvas doesn't delete the entity
                    #   group in another.
                    newGroupEntityJSON = self.tabbedPane.mainWindow.copyGroupEntity(groupEntityToSend, otherCanvas)
                    newGroupNode = None
                    if newGroupEntityJSON:
                        # Ensure that no duplicate nodes exist.
                        newGroupNode = otherCanvas.addNodeProgrammatic(newGroupEntityJSON['uid'],
                                                                       newGroupEntityJSON['Child UIDs'])
                        if not newGroupNode:
                            self.tabbedPane.entityDB.removeEntity(newGroupEntityJSON['uid'])

                    if not newGroupEntityJSON or not newGroupNode:
                        self.tabbedPane.mainWindow.MESSAGEHANDLER.info("Cannot send group node to other canvas: The "
                                                                       "nodes it contains already exist there! Make "
                                                                       "sure that the nodes in the group node you're "
                                                                       "trying to send don't exist inside other groups "
                                                                       "at the destination canvas.", popUp=True)

                otherCanvas.rearrangeGraph()
            else:
                self.tabbedPane.mainWindow.MESSAGEHANDLER.info("Please select a valid Canvas name, "
                                                               "or create a new Canvas.", popUp=True)

    def importConnectedEntities(self):
        selectedEntities = [item.uid for item in self.scene().selectedItems() if isinstance(item, Entity.BaseNode)]
        self.scene().clearSelection()
        for entity in selectedEntities:
            linkedEntities = [link[0] for link in self.tabbedPane.entityDB.getIncomingLinks(entity)
                              if link[0] not in self.scene().sceneGraph.nodes]
            linkedEntities.extend([link[1] for link in self.tabbedPane.entityDB.getOutgoingLinks(entity)
                                   if link[1] not in self.scene().sceneGraph.nodes])
            for groupEntity in [linkedGroupEntity for linkedGroupEntity in linkedEntities
                                if linkedGroupEntity.endswith('@')]:
                newEntityJSON = self.tabbedPane.mainWindow.copyGroupEntity(groupEntity, self.scene())
                if newEntityJSON:
                    newNode = self.scene().addNodeProgrammatic(newEntityJSON['uid'], newEntityJSON['Child UIDs'])
                    linkedEntities.remove(groupEntity)
                    newNode.setSelected(True)
            for regularEntity in linkedEntities:
                if regularEntity not in self.scene().sceneGraph.nodes:
                    newNode = self.scene().addNodeProgrammatic(regularEntity)
                    newNode.setSelected(True)
        self.scene().rearrangeGraph()

    def takePictureOfView(self, justViewport: bool = True, transparentBackground: bool = False) -> QtGui.QImage:
        # Need to set size and format of pic before using it.
        # Ref: https://qtcentre.org/threads/10975-Help-Export-QGraphicsView-to-Image-File
        # Rendering best optimized to rgb32 and argb32_premultiplied.
        # Ref: https://doc.qt.io/qtforpython/PySide6/QtGui/QImage.html?highlight=qimage#image-formats
        selectedItems = [item for item in self.scene().selectedItems()]
        for item in selectedItems:
            item.setSelected(False)
        if justViewport:
            picture = QtGui.QImage(self.viewport().size(), QtGui.QImage.Format_ARGB32_Premultiplied)
            # Pictures are initialised with junk data - need to clear it out before painting
            #   to avoid visual artifacts.
            picture.fill(QtGui.QColor(0, 0, 0, 0))
            picturePainter = QtGui.QPainter(picture)
            tempBrush = self.backgroundBrush()
            if transparentBackground:
                self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor.fromRgba64(0, 0, 0, 0)))
            self.render(picturePainter)
            self.setBackgroundBrush(tempBrush)
        else:
            # Convert QRectF to QRect - can't have floats when it comes to picture size.
            rectToPrint = self.scene().sceneRect().toRect()
            picture = QtGui.QImage(rectToPrint.size(), QtGui.QImage.Format_ARGB32_Premultiplied)
            # Pictures are initialised with junk data - need to clear it out before painting
            #   to avoid visual artifacts.
            picture.fill(QtGui.QColor(0, 0, 0, 0))
            picturePainter = QtGui.QPainter(picture)
            # The scene's background brush is transparent by default (for now at least, 2022/2/2)
            tempBrush = self.backgroundBrush()
            if transparentBackground:
                self.scene().setBackgroundBrush(QtGui.QBrush(QtGui.QColor.fromRgba64(0, 0, 0, 0)))
            self.scene().render(picturePainter, QtCore.QRectF(0, 0, rectToPrint.width(), rectToPrint.height()),
                                rectToPrint)
            self.scene().setBackgroundBrush(tempBrush)
        for item in selectedItems:
            item.setSelected(True)
        return picture


class CanvasScene(QtWidgets.QGraphicsScene):

    def __init__(self, parent, graph=None, positions=None, a=0, b=0, c=0, d=0, canvasName: str = 'New Canvas') -> None:
        super(CanvasScene, self).__init__(a, b, c, d, parent)
        self.itemsToLink = []
        self.linking = False
        self.itemsToAppendToGroup = []
        self.appendingToGroup = False
        self.sceneGraph = graph
        self.scenePos = positions

        # All the nodes on the canvas. Easier than looping through self.items().
        self.nodesDict = {}

        # All the links on the canvas.
        self.linksDict = {}

        if self.scenePos is None:
            self.scenePos = {}
        if self.sceneGraph is None:
            self.sceneGraph = nx.DiGraph()
        else:
            self.drawGraphOnCanvasFromOpen(canvasName)

        self.selectionChanged.connect(self.selectionChangeUpdater)
        self.resolutionThreadingLock = threading.Lock()

    # Redefined so that the BaseConnector items are not considered.
    def itemsBoundingRect(self) -> QtCore.QRectF:
        try:
            itemsX = []
            itemsY = []
            for item in self.items():
                if isinstance(item, Entity.BaseNode):
                    itemsX.append(item.pos().x())
                    itemsY.append(item.pos().y())

            minX = min(itemsX) - 210
            minY = min(itemsY) - 110
            width = max(itemsX) - minX + 260
            height = max(itemsY) - minY + 110

            return QtCore.QRectF(minX, minY, width, height)
        except ValueError:
            return QtCore.QRectF(0, 0, 0, 0)

    def addNodeToScene(self, item, x=0, y=0) -> None:
        self.nodesDict[item.uid] = item
        self.addItem(item)
        item.setPos(QtCore.QPointF(x, y))
        self.parent().mainWindow.MESSAGEHANDLER.info('Added node: ' + str(item.uid) + ' | ' + item.labelItem.text())

    def addLinkToScene(self, link: Entity.BaseConnector) -> None:
        self.linksDict[link.startItem().uid + link.endItem().uid] = link
        self.addItem(link)
        self.parent().mainWindow.MESSAGEHANDLER.info('Added link: (' + link.startItem().uid + ", " +
                                                     link.endItem().uid + ') | ' + link.labelItem.text())

    def appendSelectedItemsToGroupToggle(self) -> None:
        if self.linking:
            return
        if self.appendingToGroup:
            self.appendingToGroup = False
            self.parent().mainWindow.setGroupAppendMode(False)
            self.itemsToAppendToGroup = []
        else:
            self.parent().mainWindow.setStatus('Select a group entity to put the selected items into.')
            self.appendingToGroup = True
            self.itemsToAppendToGroup = [item for item in self.selectedItems() if isinstance(item, Entity.BaseNode)]
            self.parent().mainWindow.setGroupAppendMode(True)

    def getSelfName(self) -> str:
        return self.parent().getNameOfScene(self)

    def selectionChangeUpdater(self) -> None:
        if self.linking:
            for item in self.selectedItems():
                if item not in self.itemsToLink and self.parent().entityDB.isNode(str(item.uid)):
                    self.itemsToLink.append(item)
            if len(self.itemsToLink) > 2:
                self.itemsToLink = []
                self.clearSelection()
                self.parent().mainWindow.setStatus('Too many items selected to link, please only choose a total of 2.')
            elif len(self.itemsToLink) == 2:
                potentialUID = (self.itemsToLink[0].uid, self.itemsToLink[1].uid)
                if not self.parent().entityDB.isLink(potentialUID):
                    if self.parent().entityDB.addLink({"uid": potentialUID}) is not None:
                        self.addLinkDragDrop(self.itemsToLink[0],
                                             self.itemsToLink[1])
                        self.editLinkProperties(potentialUID)
                self.parent().mainWindow.toggleLinkingMode()

        elif self.appendingToGroup:
            selectedGroupItems = [item for item in self.selectedItems()
                                  if isinstance(item, Entity.GroupNode)]
            if len(selectedGroupItems) < 1:
                pass
            elif len(selectedGroupItems) > 1:
                self.parent().mainWindow.setStatus('Too many group items selected, please only choose one.')
            else:
                groupEntityMaybe = selectedGroupItems[0]
                if not isinstance(groupEntityMaybe, Entity.GroupNode):
                    self.parent().mainWindow.setStatus('Selected entity is not a group entity. Aborting adding new '
                                                       'items to group')
                elif groupEntityMaybe in self.itemsToAppendToGroup:
                    self.parent().mainWindow.setStatus('Set of items to add to selected group contains the group to '
                                                       'add the items to. Aborting.')
                else:
                    newJson = self.parent().entityDB.getEntity(groupEntityMaybe.uid)
                    for item in self.itemsToAppendToGroup:
                        self.removeNode(item)
                        groupEntityMaybe.addItemToGroup(item.uid)
                        newJson['Child UIDs'].append(item.uid)
                        self.sceneGraph.add_node(item.uid, groupID=groupEntityMaybe.uid)
                    self.parent().entityDB.addEntity(newJson)
                    self.appendSelectedItemsToGroupToggle()
                    # Refresh list to show new entity/entities
                    groupEntityMaybe.setSelected(False)
                    groupEntityMaybe.setSelected(True)

        self.detailsWidgetCaller()
        self.resolutionWidgetCaller()

    def resolutionWidgetCaller(self) -> None:
        self.parent().mainWindow.populateResolutionsWidget(
            [item for item in self.selectedItems() if not isinstance(item, QtWidgets.QGraphicsProxyWidget)])

    def detailsWidgetCaller(self, uid=None) -> None:
        """
        Entities and links give their uid on hover enter.
            They do not give uid on hover leave.
        This means that if a uid is given, it's a hover enter on
            either a node or a link.
        The user cannot hover over multiple items at once (but even if
            they did, the latest item would be chosen, so it works fine).
        """
        if uid is not None:
            self.parent().mainWindow.populateDetailsWidget([uid])
        else:
            # Add UIDs to list. If there are both links and nodes, remove
            #   links from list and only keep nodes.
            selectedUIDs = [item.uid for item in self.selectedItems()
                            if isinstance(item, Entity.BaseNode) or isinstance(item, Entity.BaseConnector)]
            self.parent().mainWindow.populateDetailsWidget(selectedUIDs)

    def drawGraphOnCanvasFromOpen(self, canvasName: str) -> None:
        """
        Used when a user first opens a tab that has nodes.
        Do not use for any other reason.
            This function does not check for any existing nodes or
            links on the canvas.
        """

        positions = self.scenePos
        sceneGraphNodes = self.sceneGraph.nodes

        steps = len(sceneGraphNodes)
        if steps == 0:
            return
        steps += 1
        progress = QtWidgets.QProgressDialog('Opening Canvas: ' + canvasName + ', please wait...',
                                             '', 0, steps, self.parent())
        # Remove Cancel button from progress bar (user should not be able to stop canvas from loading).
        progress.setMinimumDuration(1500)
        progress.setCancelButton(None)
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progressValue = 0

        for node in sceneGraphNodes:
            if sceneGraphNodes[node].get('groupID') is not None:
                continue
            nodeJSON = self.parent().entityDB.getEntity(node)
            if nodeJSON is None:
                self.parent().mainWindow.MESSAGEHANDLER.critical('Nodes in canvas do not exist in database!')
                sys.exit(-15)
            groupItems = None
            if nodeJSON['Entity Type'] == 'EntityGroup':
                groupItems = [item for item in sceneGraphNodes
                              if sceneGraphNodes[item].get('groupID') == nodeJSON['uid']]

            picture = nodeJSON.get('Icon')
            try:
                nodePrimaryAttribute = nodeJSON.get(
                    self.parent().mainWindow.RESOURCEHANDLER.getPrimaryFieldForEntityType(nodeJSON['Entity Type']), '')
            except IndexError:
                nodePrimaryAttribute = ''

            if groupItems is None:
                newNode = Entity.BaseNode(picture, node, nodePrimaryAttribute)
                self.addNodeToScene(newNode)
            else:
                newNode = Entity.GroupNode(picture, node, nodePrimaryAttribute)
                self.addNodeToScene(newNode)

                newGroupList = newNode.listWidget
                newGroupListGraphic = self.addWidget(newGroupList)
                newGroupListGraphic.hide()
                newNode.formGroup(groupItems, newGroupListGraphic)
                for item in groupItems:
                    self.sceneGraph.add_node(item, groupID=newNode.uid)

            newNode.setPos(QtCore.QPointF(positions[node][0], positions[node][1]))

            progressValue += 1
            progress.setValue(progressValue)

        for entity in self.nodesDict:
            self.addEntityLinkCreatorHelper(self.nodesDict[entity])

        progress.setValue(steps)
        self.parent().mainWindow.MESSAGEHANDLER.info('Loaded canvas: ' + canvasName)

    def updatePositionInDB(self, uid, x, y) -> None:
        """
        When a node changes position (i.e. it is dragged elsewhere), this
        updates the record on where the node is saved.
        """
        self.scenePos[uid] = (x, y)

    def addNodeDragDrop(self, uid, x, y, fromServer: bool = False):
        entity = self.parent().entityDB.getEntity(uid)
        if entity is None:
            return

        newNodePos = (x, y)
        picture = entity.get('Icon')

        try:
            nodePrimaryAttribute = entity.get(list(entity)[1])
        except IndexError:
            nodePrimaryAttribute = ''

        newNode = None
        if entity.get('Entity Type') == "EntityGroup":
            # We have to create a NEW Entity Group if we don't want to mess with the old one, as different
            #   canvases will have different nodes on them.
            # The 'addNode' functions assume that they've been passed whatever entity group is the correct one, i.e.
            #   either a new one being created or an old one that was copied.
            groupItems = [uid for uid in entity['Child UIDs'] if uid not in self.sceneGraph.nodes]
            if len(groupItems) > 0:
                newNode = Entity.GroupNode(picture, uid, entity['Group Name'])
                self.addNodeToScene(newNode, x, y)

                newGroupList = newNode.listWidget
                newGroupListGraphic = self.addWidget(newGroupList)
                newGroupListGraphic.hide()
                newNode.formGroup(groupItems, newGroupListGraphic)
                for item in groupItems:
                    self.sceneGraph.add_node(item, groupID=newNode.uid)
        elif entity.get('Entity Type'):
            if not fromServer:
                self.parent().mainWindow.sendLocalCanvasUpdateToServer(self.getSelfName(), uid)
            newNode = Entity.BaseNode(picture, uid, nodePrimaryAttribute)
            self.addNodeToScene(newNode, x, y)

        if newNode is not None:
            if uid in self.sceneGraph.nodes:
                del self.sceneGraph.nodes[uid]['groupID']
            else:
                self.sceneGraph.add_node(uid)
            self.scenePos[uid] = newNodePos
            self.addEntityLinkCreatorHelper(newNode)

        # Need to return entity Json to show the property editor if new
        #   entity was added.
        return newNode

    def addNodeProgrammatic(self, uid, groupItems=None, fromServer: bool = False):
        entity = self.parent().entityDB.getEntity(uid)
        if entity is None:
            return

        picture = entity.get('Icon')

        newNode = None
        if groupItems is None:
            # Do not sync group entities.
            if not fromServer:
                self.parent().mainWindow.sendLocalCanvasUpdateToServer(self.getSelfName(), uid)
            try:
                nodePrimaryAttribute = entity.get(list(entity)[1])
            except IndexError:
                nodePrimaryAttribute = ''
            newNode = Entity.BaseNode(picture, uid, nodePrimaryAttribute)
            self.addNodeToScene(newNode)
        else:
            groupItems = [uid for uid in groupItems if uid not in self.sceneGraph.nodes]
            if len(groupItems) > 0:
                newNode = Entity.GroupNode(picture, uid, entity['Group Name'])
                self.addNodeToScene(newNode)

                newGroupList = newNode.listWidget
                newGroupListGraphic = self.addWidget(newGroupList)
                newGroupListGraphic.hide()
                newNode.formGroup(groupItems, newGroupListGraphic)
                for item in groupItems:
                    self.sceneGraph.add_node(item, groupID=newNode.uid)
        if newNode is not None:
            if uid in self.sceneGraph.nodes:
                del self.sceneGraph.nodes[uid]['groupID']
            else:
                self.sceneGraph.add_node(uid)
            self.addEntityLinkCreatorHelper(newNode)

        return newNode

    def rearrangeGraph(self) -> None:
        # https://gitlab.com/graphviz/graphviz/-/merge_requests/2236
        # No triangulation library on windows yet, so sfdp can't be used there.

        graphAlgorithm = self.parent().mainWindow.SETTINGS.value("Program/GraphLayout", 'dot')
        try:
            if graphAlgorithm == 'sfdp':
                self.scenePos = nx.nx_pydot.graphviz_layout(self.sceneGraph, 'sfdp')
                xFactor = (0.40 + min(len(self.nodesDict) / 100, 10))
                yFactor = (0.40 + min(len(self.nodesDict) / 100, 10))
            elif graphAlgorithm == 'neato':
                self.scenePos = nx.nx_pydot.graphviz_layout(self.sceneGraph, 'neato')
                xFactor = (3 + (0.30 + min(len(self.nodesDict) / 100, 10)))
                yFactor = (3 + (0.30 + min(len(self.nodesDict) / 100, 10)))
            else:
                # Default algorithm is 'dot', when nothing else is selected.

                # No real 'links' to group nodes by default (links to internal nodes don't count). This means that the
                #   'dot' algorithm can create odd graphs where group nodes are concerned.
                # To fix this, we will duplicate the scene graph, add links between the group nodes and the
                #   outside world, and use that clone for positions.
                currGraphClone = nx.DiGraph(self.sceneGraph)

                for edgeParentUID, edgeChild in dict(currGraphClone.edges):
                    potentialGroupIDOne = currGraphClone.nodes[edgeParentUID].get('groupID', edgeParentUID)
                    potentialGroupIDTwo = currGraphClone.nodes[edgeChild].get('groupID', edgeChild)
                    # Nothing happens if edge already exists. If not, edge is created.
                    # These edges will not be visible on the actual graph generated.
                    currGraphClone.add_edge(potentialGroupIDOne, potentialGroupIDTwo)

                # Only use nodes that are represented on the graph, else we can end up with nodes on the
                #   other side of the world.
                currGraphClone = nx.DiGraph(self.sceneGraph)
                for node in dict(currGraphClone.nodes):
                    if currGraphClone.nodes[node].get('groupID') is not None:
                        currGraphClone.remove_node(node)

                pdGraph = nx.drawing.nx_pydot.to_pydot(currGraphClone)
                pdGraph.set_layout('dot')
                pdGraph.set_rankdir('BT')
                pdGraphNX = nx.nx_pydot.from_pydot(pdGraph)
                self.scenePos = nx.drawing.nx_pydot.pydot_layout(pdGraphNX)
                xFactor = 0.70
                yFactor = 2.75
        except Exception as exc:
            self.parent().mainWindow.MESSAGEHANDLER.error('Failed drawing graph with selected algorithm, falling back '
                                                          'to using "dot" algorithm: ' + str(exc), popUp=False)
            # If something goes wrong (e.g. the selected algorithm isn't found), use the dot algorithm.
            # See comments for 'dot' algorithm.
            currGraphClone = nx.DiGraph(self.sceneGraph)

            for edgeParentUID, edgeChild in dict(currGraphClone.edges):
                potentialGroupIDOne = currGraphClone.nodes[edgeParentUID].get('groupID', edgeParentUID)
                potentialGroupIDTwo = currGraphClone.nodes[edgeChild].get('groupID', edgeChild)
                currGraphClone.add_edge(potentialGroupIDOne, potentialGroupIDTwo)

            currGraphClone = nx.DiGraph(self.sceneGraph)
            for node in dict(currGraphClone.nodes):
                if currGraphClone.nodes[node].get('groupID') is not None:
                    currGraphClone.remove_node(node)

            pdGraph = nx.drawing.nx_pydot.to_pydot(currGraphClone)
            pdGraph.set_layout('dot')
            pdGraph.set_rankdir('BT')
            pdGraphNX = nx.nx_pydot.from_pydot(pdGraph)
            self.scenePos = nx.drawing.nx_pydot.pydot_layout(pdGraphNX)
            xFactor = 0.70
            yFactor = 2.75

        for node in self.nodesDict:
            # Scale graph with number of nodes.
            x = self.scenePos[node][0] * xFactor
            y = self.scenePos[node][1] * yFactor
            self.scenePos[node] = (x, y)
            self.nodesDict[node].setPos(QtCore.QPointF(x, y))

        self.adjustSceneRect()

    def rearrangeGraphTimeline(self) -> None:
        # Arrange nodes in a half-tree Left to Right graph based on the time they were created.
        #  -----------
        #       \         etc...
        #        -----

        nodesOnCanvas = {}
        for node in self.nodesDict:
            try:
                # Tiny differences in milliseconds are not considered to be significant.
                entityDate = datetime.fromisoformat(
                    self.parent().entityDB.getEntity(node)['Date Created']).replace(microsecond=0)
            except (TypeError, ValueError):
                # Should never happen, but we will handle it if it does.
                self.parent().mainWindow.MESSAGEHANDLER.warning('Entity without valid Date Created: ' + str(node))
                entityDate = datetime.now().replace(microsecond=0)
            if entityDate not in nodesOnCanvas:
                nodesOnCanvas[entityDate] = [node]
            else:
                nodesOnCanvas[entityDate].append(node)
        sortedDates = sorted(nodesOnCanvas)
        xValue = 0
        yValue = 0
        for dateIndex in range(len(sortedDates)):
            for entityUID in nodesOnCanvas[sortedDates[dateIndex]]:
                self.scenePos[entityUID] = (xValue, yValue)
                self.nodesDict[entityUID].setPos(QtCore.QPointF(xValue, yValue))
                yValue += 150
            yValue = 0
            xValue += 850

        self.adjustSceneRect()

    def adjustSceneRect(self) -> None:
        newRect = self.itemsBoundingRect()
        self.setSceneRect(newRect)

    def addEntityLinkCreatorHelper(self, entity: Entity.BaseNode) -> None:
        """
        Once an entity is created on a canvas, there needs to be a check to ensure that all necessary links
        to and from that entity are drawn. This function does that.
        :param entity:
        :return:
        """
        currentNodes = self.sceneGraph.nodes
        entityUID = entity.uid

        # Get all incoming and outgoing edges of the entity we are concerned with.
        # If it's a group node, also get the links of the entities that are involved.
        incomingLinks = list(self.parent().entityDB.getIncomingLinks(entityUID))
        outgoingLinks = list(self.parent().entityDB.getOutgoingLinks(entityUID))
        if isinstance(entity, Entity.GroupNode):
            for childUID in entity.groupedNodesUid:
                incomingLinks += list(self.parent().entityDB.getIncomingLinks(childUID))
                outgoingLinks += list(self.parent().entityDB.getOutgoingLinks(childUID))

        [self.addLinkProgrammatic(link, self.parent().entityDB.getLink(link)['Resolution'])
         for link in incomingLinks if link[0] in currentNodes and link[0] != link[1]]
        [self.addLinkProgrammatic(link, self.parent().entityDB.getLink(link)['Resolution'])
         for link in outgoingLinks if link[1] in currentNodes and link[0] != link[1]]

    def moveNodeProgrammatic(self, item, pos: QtCore.QPointF) -> None:
        """
        Move the specified item to a new position on the canvas.
        :param pos: Optional, specify the new position for the item manually. Otherwise, the new position
        is automatically generated.
        :param item: The entity item to move.
        :return:
        """
        uid = item.uid
        allNodes = self.scenePos.keys()
        if uid not in allNodes:
            return

        item.setPos(pos)
        self.scenePos[uid] = (pos.x(), pos.y())

    def addLinkDragDrop(self, origin: Entity.BaseNode, destination: Entity.BaseNode, name: str = 'None',
                        fromServer: bool = False) -> None:
        """
        Not just for links dragged and dropped, this function is used to create a link when the
        entities to join together are known.

        Parameters:
            :param fromServer:
            :param origin: Entity.BaseNode, the parent node
            :param destination: Entity.BaseNode, the child node
            :param name:
        """
        linkUID = (origin.uid, destination.uid)
        linkStringUID = origin.uid + destination.uid
        if linkStringUID in self.linksDict:
            linkToEdit = self.linksDict[linkStringUID]
            if linkToEdit.labelItem.text() != name and linkUID not in linkToEdit.uid:
                linkToEdit.updateLabel('')
            linkToEdit.uid.add(linkUID)
        else:
            self.sceneGraph.add_edge(origin.uid, destination.uid)
            self.addLinkToScene(Entity.BaseConnector(origin, destination, name))

        if not fromServer:
            self.parent().mainWindow.sendLocalCanvasUpdateToServer(self.getSelfName(), linkUID)

    def addLinkProgrammatic(self, uid: tuple, name: str = 'None', fromServer: bool = False) -> None:
        if uid is None:
            self.parent().messageHandler.error("Cannot add link to canvas: Invalid link UID.")
            return

        parentItem = self.getVisibleNodeForUID(uid[0])
        childItem = self.getVisibleNodeForUID(uid[1])
        if parentItem is None or childItem is None:
            return

        linkStringUID = parentItem.uid + childItem.uid
        if linkStringUID in self.linksDict:
            linkToEdit = self.linksDict[linkStringUID]
            if linkToEdit.labelItem.text() != name and uid not in linkToEdit.uid:
                linkToEdit.updateLabel('')
            linkToEdit.uid.add(uid)
        else:
            self.sceneGraph.add_edge(uid[0], uid[1])
            self.addLinkToScene(Entity.BaseConnector(parentItem, childItem, name, uid))

        if not fromServer:
            self.parent().mainWindow.sendLocalCanvasUpdateToServer(self.getSelfName(), uid)

    def getVisibleNodeForUID(self, uid: str):
        """
        This gets the node on the canvas that the uid corresponds to, or the visible group node that the entity
        with the given uid is in.

        :param uid:
        :return:
        """
        # There is an assumption made here: That a canvas that contains a grouped node will also contain the group
        #   that the node is in. This should be pretty safe. If not, the canvas is probably in a terrible state.
        # Will not assume that the canvas is unrecoverable, so it's just an error instead of critical.
        nodes = self.sceneGraph.nodes
        if uid in nodes:
            group = nodes[uid].get('groupID')
            while group is not None:
                uid = group
                group = nodes[uid].get('groupID')
            try:
                return self.nodesDict[uid]
            except KeyError:
                self.parent().messageHandler.error('Canvas state is undefined: Tried to get a node not present in the '
                                                   'canvas, uid: ' + str(uid))
        return None

    def getVisibleLinkForUID(self, uid: tuple):
        """
        Try to get the link on the canvas that the uid corresponds to.
        """
        linkStringUID = uid[0] + uid[1]
        return self.linksDict.get(linkStringUID, None)

    def removeGroupNodeLinksForUID(self, groupUID, nodeUID) -> None:
        edgesToDelete = {}
        # Search all links
        for link in self.linksDict:
            edgesToDelete[link] = []
            # If a link is drawn to or from the group node in question...
            if groupUID in link:
                for linkUID in self.linksDict[link].uid:
                    # ... and if the link concerns the node we're looking for...
                    if nodeUID in linkUID:
                        # Then remove the UID from the link, and delete the link if it has no more UIDs.
                        edgesToDelete[link].append(linkUID)

        for edgeToDelete in edgesToDelete:
            # Remove UIDs from list, and delete the link if no more UIDs are left
            self.linksDict[edgeToDelete].uid = [linkToStayUID for linkToStayUID in self.linksDict[edgeToDelete].uid
                                                if linkToStayUID not in edgesToDelete[edgeToDelete]]
            if len(self.linksDict[edgeToDelete].uid) == 0:
                self.removeEdge(self.linksDict[edgeToDelete])

    def removeUIDFromLink(self, linkUIDToRemove: tuple) -> None:
        for link in dict(self.linksDict):
            if linkUIDToRemove in self.linksDict[link].uid:
                self.linksDict[link].uid.remove(linkUIDToRemove)

                if len(self.linksDict[link].uid) == 0:
                    self.removeEdge(self.linksDict[link])
                # The link uid to remove should only be in one link
                break

    def editEntityProperties(self, entityUID) -> None:
        # Dereference existing json object before potentially re-adding.
        entityJSON = dict(self.parent().entityDB.getEntity(entityUID))
        pEditor = PropertiesEditor(self, entityJSON, True)
        if pEditor.exec_():
            # Adding entity with the same UID just overwrites properties.
            # No need to update the label manually here - Since we re-added the entity to the database,
            #   the label will be updated by the software automatically.
            self.parent().entityDB.addEntity(pEditor.objectJson)
            item = self.nodesDict[entityUID]
            item.removeFromGroup(item.iconItem)
            self.removeItem(item.iconItem)

            pictureByteArray = pEditor.objectJson['Icon']
            item.pixmapItem = QtGui.QPixmap()
            item.pixmapItem.loadFromData(pictureByteArray)
            if pictureByteArray.data().startswith(b'<svg '):
                item.iconItem = QGraphicsSvgItem()
                item.iconItem.renderer().load(pictureByteArray)
                item.iconItem.setElementId("")  # Force recalculation of geometry, else this looks like 1 pixel.
            else:
                item.iconItem = QGraphicsPixmapItem(item.pixmapItem)

            item.iconItem.setPos(item.pos())
            item.addToGroup(item.iconItem)
            primaryField = pEditor.objectJson[list(pEditor.objectJson)[1]]
            self.parent().messageHandler.info('Edited node: ' + pEditor.objectJson['uid'] + ' | ' + primaryField)

    def editLinkProperties(self, linkUID: tuple) -> None:
        """
        Only link graphical items with 1 link uid can be edited.
        :param linkUID:
        :return:
        """
        if not isinstance(linkUID, tuple):
            self.parent().messageHandler.warning('Cannot edit a set of links at once. Please make sure that '
                                                 'the selected connector represents only one link.', popUp=True)
            return
        linkJSON = self.parent().entityDB.getLink(linkUID)
        pEditor = PropertiesEditor(self, linkJSON, False)
        if pEditor.exec_():
            # Adding link with the same UID just overwrites properties.
            self.parent().entityDB.addLink(pEditor.objectJson, overwrite=True)
            self.parent().messageHandler.info('Edited link: ' + str(pEditor.objectJson['uid']) + ' | ' +
                                              pEditor.objectJson['Resolution'])

    # Because the entities on each canvas are stored in dicts, and dicts are ordered, group nodes will always
    # come after the nodes they contain.
    def groupSelectedItems(self):
        items = [item for item in self.selectedItems() if isinstance(item, Entity.BaseNode)]
        for item in items:
            if isinstance(item, Entity.GroupNode):
                self.parent().messageHandler.warning('Cannot create nested group nodes. For de-cluttering, it is '
                                                     'suggested that you move the nodes you are interested in '
                                                     'into a new canvas.', popUp=True)
                return
        itemUIDs = [item.uid for item in items]
        if len(itemUIDs) > 1:
            newEntity = self.parent().entityDB.addEntity(
                {'Group Name': 'Entity Group', 'Child UIDs': itemUIDs, 'Entity Type': 'EntityGroup'})
            uid = newEntity['uid']
            [self.removeNode(item) for item in items]
            groupNode = self.addNodeProgrammatic(uid, itemUIDs)
            if groupNode is not None:
                self.rearrangeGraph()
            return groupNode
        else:
            self.parent().mainWindow.setStatus('Please select more than one node to create a Group node.')

    def ungroupSelectedItems(self) -> None:
        groups = [item for item in self.selectedItems() if isinstance(item, Entity.GroupNode)]
        for group in groups:
            newNodesUIDs = group.groupedNodesUid
            self.removeNode(group)
            for newNodeUID in newNodesUIDs:
                # Cannot set fromServer to True - could drag group nodes from different canvas,
                #   and ungroup them here.
                if newNodeUID not in self.nodesDict:
                    self.addNodeProgrammatic(newNodeUID)
        self.rearrangeGraph()

    def deleteSelectedItems(self) -> None:
        items = self.selectedItems()
        for item in items:
            if isinstance(item, Entity.BaseNode):
                if isinstance(item, Entity.GroupNode):
                    if item.listProxyWidget is not None:
                        item.listProxyWidget.hide()
                self.removeNode(item)

    def removeNode(self, nodeItem: Entity.BaseNode) -> None:
        if not isinstance(nodeItem, Entity.BaseNode) or self.sceneGraph.nodes.get(nodeItem.uid) is None:
            # Do not remove invalid nodes, or nodes that do not exist.
            return
        uid = nodeItem.uid
        nodeItem.hide()
        self.nodesDict.pop(uid)
        for edge in nodeItem.connectors:
            self.removeEdge(edge)
        if nodeItem in self.selectedItems():
            self.clearSelection()
        self.removeItem(nodeItem)
        # Node already deleted
        try:
            self.sceneGraph.remove_node(uid)
        except nx.exception.NetworkXError:
            pass
        try:
            self.scenePos.pop(uid)
        except KeyError:
            pass
        if isinstance(nodeItem, Entity.GroupNode):
            for childUID in nodeItem.groupedNodesUid:
                self.sceneGraph.remove_node(childUID)
            self.parent().mainWindow.deleteSpecificEntity(uid)
        del nodeItem

    def removeEdge(self, edgeItem: Entity.BaseConnector) -> None:
        try:
            self.linksDict.pop(edgeItem.myStartItem.uid + edgeItem.myEndItem.uid)
        except KeyError:
            # Edge already removed from linksDict.
            pass
        uidProper = (edgeItem.myStartItem.uid, edgeItem.myEndItem.uid)
        edgeItem.hide()
        edgeItem.myStartItem.removeConnector(self)
        edgeItem.myEndItem.removeConnector(self)
        if edgeItem in self.selectedItems():
            self.clearSelection()
        try:
            self.sceneGraph.remove_edge(uidProper[0], uidProper[1])
        except nx.exception.NetworkXError:
            # Thrown when an edge is already deleted.
            pass
        # Could be the case that some link graphics are duplicated or left hanging.
        #   This would clear them out.
        if edgeItem.scene() == self:
            self.removeItem(edgeItem)
        del edgeItem

    def syncCanvas(self, canvas_nodes: dict, canvas_edges: dict) -> None:
        """
        Merge canvas updates from remote client into this canvas.
        """
        newNodes = [node for node in canvas_nodes if node not in self.nodesDict and
                    self.parent().mainWindow.LENTDB.getEntity(node)['Entity Type'] != 'EntityGroup']
        # newGroupNodes = [y for y in newNodes
        #                 if self.parent().mainWindow.LENTDB.getEntity(y)['Entity Type'] == 'EntityGroup']
        # newNodesInGroup = []
        # for groupNode in newGroupNodes:
        #    entityJson = self.parent().mainWindow.LENTDB.getEntity(groupNode)
        #    self.addNodeProgrammatic(groupNode, entityJson['Child UIDs'], fromServer=True)
        #    newNodesInGroup += entityJson['Child UIDs']
        for node in newNodes:  # [z for z in newNodes if z not in newNodesInGroup]:
            self.addNodeProgrammatic(node, fromServer=True)

        # Edges technically only added if the related nodes are already created,
        #   otherwise addNodeProgrammatic should add them automatically.
        edges = [edge for edge in canvas_edges if (edge[0] + edge[1] not in self.linksDict) and
                 (edge[0] in self.nodesDict and edge[1] in self.nodesDict)]
        for edge in edges:
            self.addLinkProgrammatic(edge, canvas_edges.get(edge)['Resolution'], fromServer=True)
        self.rearrangeGraph()


class PropertiesEditor(QtWidgets.QDialog):
    def __init__(self, canvas, objectJson, isNode: True):
        super().__init__()
        self.setModal(True)
        self.isEditingNode = isNode

        # self.setLayout(QtWidgets.QGridLayout())
        self.setWindowTitle("Properties Editor")
        self.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)
        self.setMinimumSize(500, 300)
        self.objectJson = objectJson
        self.canvas = canvas

        self.itemProperties = QtWidgets.QFormLayout()
        for key in objectJson:
            if key in ('uid', 'Entity Type', 'Date Last Edited', 'Child UIDs'):
                continue
            keyField = QtWidgets.QLabel(key)
            if key == "Notes":
                valueField = QtWidgets.QPlainTextEdit(objectJson[key])
            elif key == 'Icon':
                valueField = PropertiesEditorIconField(objectJson[key], objectJson['uid'], self.canvas)
            elif key == 'File Path':
                valueField = PropertiesEditorFilePathField(objectJson[key])
            else:
                valueField = QtWidgets.QLineEdit(str(objectJson[key]))
            self.itemProperties.addRow(keyField, valueField)
        acceptButton = QtWidgets.QPushButton("Confirm")
        acceptButton.setStyleSheet(Stylesheets.BUTTON_STYLESHEET)
        cancelButton = QtWidgets.QPushButton("Cancel")
        cancelButton.setStyleSheet(Stylesheets.BUTTON_STYLESHEET)
        acceptButton.setAutoDefault(True)
        acceptButton.setDefault(True)
        acceptButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)
        self.itemProperties.addRow(cancelButton, acceptButton)

        self.setLayout(self.itemProperties)

    def accept(self):
        for row in range(self.itemProperties.rowCount()):
            key = self.itemProperties.itemAt(
                row, self.itemProperties.LabelRole).widget().text()
            if key == "Notes":
                value = self.itemProperties.itemAt(
                    row, self.itemProperties.FieldRole).widget().toPlainText()
            elif key == 'Icon':
                value = self.itemProperties.itemAt(
                    row, self.itemProperties.FieldRole).widget().pictureByteArray
            elif key == 'File Path':
                value = self.itemProperties.itemAt(
                    row, self.itemProperties.FieldRole).widget().text()
                projectFilesPath = Path(self.canvas.parent().mainWindow.SETTINGS.value("Project/FilesDir"))
                newPath = projectFilesPath / value
                if not newPath.is_relative_to(projectFilesPath):
                    value = str(self.canvas.parent().mainWindow.URLMANAGER.moveURLToProjectFilesHelperIfNeeded(
                        Path(value)))
                elif not newPath.exists():
                    value = 'None'
            else:
                value = self.itemProperties.itemAt(
                    row, self.itemProperties.FieldRole).widget().text()
            # The last row is the Cancel / Accept buttons.
            if key != "Cancel":
                self.objectJson[key] = value

        # Now that we've assigned all the values, validate them.
        # Less efficient than doing that as we go, but it doesn't really matter; there's unlikely to be entities
        #   with enough fields for this to matter.
        if self.isEditingNode:
            isValid = self.canvas.parent().mainWindow.RESOURCEHANDLER.validateAttributesOfEntity(self.objectJson)
            if isValid is True:
                super().accept()
            elif isinstance(isValid, str):
                self.canvas.parent().mainWindow.MESSAGEHANDLER.error('Entity fields contain invalid values: ' + isValid,
                                                                     exc_info=False)
            else:
                self.canvas.parent().mainWindow.MESSAGEHANDLER.error('Error occurred when checking validity of entity '
                                                                     'field values.')
        else:
            super().accept()


class PropertiesEditorFilePathField(QtWidgets.QLineEdit):

    def __init__(self, value):
        super(PropertiesEditorFilePathField, self).__init__()
        self.setText(str(value))

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        selectedPath = QtWidgets.QFileDialog().getOpenFileName(parent=self, caption='Select File Path',
                                                               options=QtWidgets.QFileDialog.DontUseNativeDialog)[0]
        if selectedPath != '':
            self.setText(str(Path(selectedPath).absolute()))

        super(PropertiesEditorFilePathField, self).mousePressEvent(event)


class PropertiesEditorIconField(QtWidgets.QLabel):

    def __init__(self, pictureByteArray, uid, canvas):
        super(PropertiesEditorIconField, self).__init__()
        self.pictureByteArray = pictureByteArray
        pixmapToSet = QtGui.QPixmap()
        pixmapToSet.loadFromData(pictureByteArray)
        self.setPixmap(pixmapToSet)
        self.uid = uid
        self.canvas = canvas

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:

        selectedPath = QtWidgets.QFileDialog().getOpenFileName(parent=self, caption='Select New Icon',
                                                               options=QtWidgets.QFileDialog.DontUseNativeDialog,
                                                               filter="Image Files (*.png *.jpg *.bmp *.svg)")[0]
        if selectedPath != '':
            try:
                filePath = Path(selectedPath)

                with open(filePath, 'rb') as newIconFile:
                    fileContents = newIconFile.read()
                if fileContents.startswith(b'<svg '):
                    widthRegex = re.compile(b' width="\d*" ')
                    for widthMatches in widthRegex.findall(fileContents):
                        fileContents = fileContents.replace(widthMatches, b' ')
                    heightRegex = re.compile(b' height="\d*" ')
                    for heightMatches in heightRegex.findall(fileContents):
                        fileContents = fileContents.replace(heightMatches, b' ')
                    fileContents = fileContents.replace(b'<svg ', b'<svg height="40" width="40" ', 1)
                    self.pictureByteArray = QtCore.QByteArray(fileContents)
                else:
                    image = Image.open(selectedPath)
                    thumbSize = 40, 40
                    thumbnail = ImageQt(image.resize(thumbSize))
                    self.pictureByteArray = QtCore.QByteArray()
                    imageBuffer = QtCore.QBuffer(self.pictureByteArray)

                    imageBuffer.open(QtCore.QIODevice.WriteOnly)

                    thumbnail.save(imageBuffer, "PNG")
                    imageBuffer.close()

                pixmapToSet = QtGui.QPixmap()
                pixmapToSet.loadFromData(self.pictureByteArray)
                self.setPixmap(pixmapToSet)
            except ValueError as ve:
                # Image type is unsupported (for ImageQt)
                # Supported types: 1, L, P, RGB, RGBA
                self.canvas.parent().mainWindow.MESSAGEHANDLER.warning(
                    'Invalid Image selected: ' + str(ve), popUp=True)

        super(PropertiesEditorIconField, self).mousePressEvent(event)


class SendToOtherTabCanvasSelector(QtWidgets.QDialog):

    def __init__(self, canvasNames: list):
        super(SendToOtherTabCanvasSelector, self).__init__()
        self.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)
        self.setModal(True)
        self.setWindowTitle('Move Selected Entities to New Canvas')

        sendToOtherCanvasLayout = QtWidgets.QGridLayout()
        self.setLayout(sendToOtherCanvasLayout)
        self.canvasNameSelector = QtWidgets.QComboBox()
        self.canvasNameSelector.addItems(canvasNames)
        descriptionLabel = QtWidgets.QLabel(
            "Select an available Canvas to move the selected entities into:")
        canvasNameLabel = QtWidgets.QLabel("Canvas Name:")

        confirmButton = QtWidgets.QPushButton("Confirm")
        confirmButton.setAutoDefault(True)
        confirmButton.setDefault(True)
        confirmButton.clicked.connect(self.accept)
        cancelButton = QtWidgets.QPushButton("Cancel")
        cancelButton.clicked.connect(self.reject)

        sendToOtherCanvasLayout.addWidget(descriptionLabel, 0, 0, 1, 3)
        sendToOtherCanvasLayout.addWidget(canvasNameLabel, 1, 0, 1, 1)
        sendToOtherCanvasLayout.addWidget(self.canvasNameSelector, 1, 1, 1, 2)
        sendToOtherCanvasLayout.addWidget(cancelButton, 2, 0, 1, 1)
        sendToOtherCanvasLayout.addWidget(confirmButton, 2, 1, 1, 2)
