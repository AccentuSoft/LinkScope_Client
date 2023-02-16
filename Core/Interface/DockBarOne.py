#!/usr/bin/env python3
from json import dumps
from Core.Interface.Entity import BaseNode
from PySide6 import QtWidgets, QtCore, QtGui


class DockBarOne(QtWidgets.QDockWidget):

    def initialiseLayout(self) -> None:
        childWidget = QtWidgets.QTabWidget()
        nodeTabChildWidget = QtWidgets.QWidget()
        docsTabChildWidget = QtWidgets.QWidget()
        nodeTabChildWidget.setLayout(QtWidgets.QGridLayout())
        docsTabChildWidget.setLayout(QtWidgets.QGridLayout())
        self.setWidget(childWidget)

        childWidget.addTab(nodeTabChildWidget, "Node Operations")
        childWidget.addTab(docsTabChildWidget, "Documents")

        nodeTabChildWidget.layout().addWidget(self.nodesPalette)
        nodeTabChildWidget.layout().addWidget(self.resolutionsPalette)
        docsTabChildWidget.layout().addWidget(self.documentsList)
        docsTabChildWidget.layout().addWidget(self.existingEntitiesPalette)

        worldDocToggle = ToggleWorldDocButton(self, self.parent())
        docsTabChildWidget.layout().addWidget(worldDocToggle)

    def __init__(self,
                 mainWindow,
                 resolutionManager,
                 resourceHandler,
                 entityDatabase,
                 title="DockBar One") -> None:
        super(DockBarOne, self).__init__(parent=mainWindow)
        self.resolutionManager = resolutionManager
        self.resourceHandler = resourceHandler
        self.lentDB = entityDatabase
        self.setAllowedAreas(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea |
                             QtCore.Qt.DockWidgetArea.RightDockWidgetArea)
        self.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable |
                         QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable |
                         QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.setWindowTitle(title)
        self.setObjectName(title)

        self.nodesPalette = NodeList(self.resourceHandler, self)
        self.resolutionsPalette = ResolutionList(self.resolutionManager,
                                                 self.lentDB,
                                                 self.parent(),
                                                 self)
        self.documentsList = DocList(self.resourceHandler, self)
        self.existingEntitiesPalette = EntityList(self.lentDB, self.parent(), self)

        self.initialiseLayout()


class ToggleWorldDocButton(QtWidgets.QPushButton):

    def __init__(self, parent=None, mainWindow=None) -> None:
        super(ToggleWorldDocButton, self).__init__(parent=parent)
        self.mainWindow = mainWindow
        self.setText("Toggle Detailed View")
        self.clicked.connect(self.buttonPressed)

    def buttonPressed(self) -> None:
        if self.mainWindow is not None:
            self.mainWindow.toggleWorldDoc()


class EntityList(QtWidgets.QTreeWidget):

    def __init__(self, entityDB, mainWindow, parent=None):
        super(EntityList, self).__init__(parent=parent)

        self.entityDB = entityDB
        self.mainWindow = mainWindow
        self.setDragEnabled(True)
        self.setHeaderLabels(['Entity List'])
        self.setAlternatingRowColors(False)
        self.setMinimumWidth(200)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.menu = QtWidgets.QMenu()

        actionDelete = QtGui.QAction('Delete Selected Items',
                                     self.menu,
                                     statusTip="Delete the selected entities from the database.",
                                     triggered=self.deleteSelectedItems)
        self.menu.addAction(actionDelete)

        actionAddToCurrentCanvas = QtGui.QAction('Add Selected Items to Current Canvas',
                                                 self.menu,
                                                 statusTip="Add the selected entities to the current canvas.",
                                                 triggered=self.addItemsToCurrentCanvas)
        self.menu.addAction(actionAddToCurrentCanvas)

        self.entityCategories: dict = {}
        self.entityTypes: dict = {}
        self.loadEntities()

    def loadEntities(self) -> None:
        self.clear()
        self.entityCategories = {}
        self.entityTypes = {}

        for category in self.mainWindow.RESOURCEHANDLER.getEntityCategories():
            catTreeItem = QtWidgets.QTreeWidgetItem(self, [category])
            self.entityCategories[category] = catTreeItem

        for category in self.entityCategories:
            for entityType in self.mainWindow.RESOURCEHANDLER.getAllEntitiesInCategory(category):
                typeTreeItem = QtWidgets.QTreeWidgetItem(self.entityCategories[category], [entityType])
                self.entityTypes[entityType] = typeTreeItem

        allEntities = self.entityDB.getAllEntities()
        for entity in allEntities:
            topItem = self.entityTypes[entity['Entity Type']]
            primaryAttr = entity[list(entity)[1]]
            pixmapIcon = QtGui.QPixmap()
            pixmapIcon.loadFromData(entity['Icon'])
            EntityWidget(topItem,
                         entity['uid'],
                         QtGui.QIcon(pixmapIcon),
                         primaryAttr)

        # Hide entity types and categories with no item instances (children):
        for category in self.entityCategories:
            childrenHidden = 0
            for entityTypeIndex in range(self.entityCategories[category].childCount()):
                entityTypeItem = self.entityCategories[category].child(entityTypeIndex)
                if entityTypeItem.childCount() == 0:
                    entityTypeItem.setHidden(True)
                    childrenHidden += 1
            if childrenHidden == self.entityCategories[category].childCount():
                self.entityCategories[category].setHidden(True)

    def addEntity(self, entityJson) -> None:
        primaryAttr = entityJson[list(entityJson)[1]]
        entityTypeItem = self.entityTypes[entityJson['Entity Type']]
        for entityNo in range(entityTypeItem.childCount()):
            child = entityTypeItem.child(entityNo)
            if child.uid == entityJson['uid']:
                child.setText(0, primaryAttr)
                return
        pixmapIcon = QtGui.QPixmap()
        pixmapIcon.loadFromData(entityJson['Icon'])
        EntityWidget(entityTypeItem,
                     entityJson['uid'],
                     QtGui.QIcon(pixmapIcon),
                     primaryAttr)
        # Un-hide parents of item, if they were hidden.
        if entityTypeItem.isHidden():
            entityTypeItem.setHidden(False)
            entityTypeItem.parent().setHidden(False)

    def removeEntity(self, entityJson) -> None:
        entityType = self.entityTypes[entityJson['Entity Type']]
        for entityNo in range(entityType.childCount()):
            child = entityType.child(entityNo)
            if child.uid == entityJson['uid']:
                entityType.removeChild(child)
                del child
                if entityType.childCount() == 0:
                    entityType.setHidden(True)
                    entityCategory = entityType.parent()
                    entityCategory.setHidden(True)
                    for childID in range(entityCategory.childCount()):
                        child = entityCategory.child(childID)
                        if not child.isHidden():
                            entityCategory.setHidden(False)
                            break
                break

    def mouseMoveEvent(self, event) -> None:
        """
        Handle dragging of entities onto canvas.
        """
        if event.buttons() == QtCore.Qt.MouseButton.LeftButton:
            itemDragged = self.itemAt(event.pos())
        else:
            return

        # Categories & entity names don't have uids.
        try:
            if itemDragged.uid is None:
                return
        except Exception:
            return

        self.setCurrentItem(itemDragged)
        drag = QtGui.QDrag(self)
        mimeData = QtCore.QMimeData()

        mimeData.setText(dumps({'uid': itemDragged.uid}))
        drag.setMimeData(mimeData)

        # All Entities should have icons, but you never know.
        pixmap = None
        if itemDragged.icon(0) is not None:
            pixmap = itemDragged.icon(0).pixmap(40, 40)
            drag.setPixmap(pixmap)
        drag.setHotSpot(QtCore.QPoint(pixmap.rect().width() // 2, pixmap.rect().height() // 2))
        drag.exec_()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        super(EntityList, self).mousePressEvent(event)

        if event.button() == QtGui.Qt.MouseButton.RightButton:
            itemDragged = self.itemAt(event.pos())
            if isinstance(itemDragged, EntityWidget):
                self.menu.exec(QtGui.QCursor.pos())

    def deleteSelectedItems(self) -> None:
        itemsToDel = [item.uid for item in self.selectedItems() if isinstance(item, EntityWidget)]
        for itemUID in itemsToDel:
            self.mainWindow.deleteSpecificEntity(itemUID)

    def addItemsToCurrentCanvas(self) -> None:
        currentScene = self.mainWindow.centralWidget().tabbedPane.getCurrentScene()
        itemsToAdd = [item.uid for item in self.selectedItems() if isinstance(item, EntityWidget) and
                      item.uid not in currentScene.sceneGraph.nodes]
        for itemUID in itemsToAdd:
            if itemUID.endswith('@'):
                newGroupEntity = self.mainWindow.copyGroupEntity(itemUID, currentScene)
                if newGroupEntity is not None:
                    currentScene.addNodeProgrammatic(newGroupEntity['uid'], newGroupEntity['Child UIDs'])
            else:
                currentScene.addNodeProgrammatic(itemUID)
        currentScene.rearrangeGraph()


class EntityWidget(QtWidgets.QTreeWidgetItem):

    def __init__(self, parent, uid=None, icon=None, text="") -> None:
        super(EntityWidget, self).__init__(parent, [text])
        self.uid = uid
        if icon is not None:
            self.setIcon(0, icon)


class DocList(QtWidgets.QTreeWidget):

    def __init__(self, resourceHandler, parent=None) -> None:
        super(DocList, self).__init__(parent=parent)

        self.resourceHandler = resourceHandler
        self.setAlternatingRowColors(False)
        self.setHeaderLabels(['Files Loaded'])
        self.uploadingFileWidgets = []
        self.uploadedFileWidgets = []
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)

    def addUploadingFileToList(self, fileName: str) -> None:
        newWidget = DocWidget(self,
                              QtGui.QIcon(self.resourceHandler.getIcon("uploading")), fileName)
        self.uploadingFileWidgets.append(newWidget)

    def finishUploadingFile(self, fileName: str) -> None:
        # Remove uploading file. Server will send updated file list.
        for doc in list(self.uploadingFileWidgets):
            if doc.getFileName() == fileName:
                self.takeTopLevelItem(self.indexOfTopLevelItem(doc))
                self.uploadingFileWidgets.remove(doc)
                break

    def updateFileListFromServer(self, fileList) -> None:
        # If disconnected from server, or project has an empty file list, clear the widget.
        if not fileList:
            self.clear()
            self.uploadingFileWidgets = []
            self.uploadedFileWidgets = []
            return

        for fileName in fileList:
            if fileName in [uploadedFileWidget.getFileName() for uploadedFileWidget in self.uploadedFileWidgets]:
                continue
            newWidget = DocWidget(self, None, fileName)
            self.uploadedFileWidgets.append(newWidget)


class DocWidget(QtWidgets.QTreeWidgetItem):

    def __init__(self, parent, icon=None, text="") -> None:
        super(DocWidget, self).__init__(parent, [text])
        if icon is not None:
            self.setIcon(0, icon)

    def getFileName(self) -> str:
        return self.text(0)


class ResolutionList(QtWidgets.QTreeWidget):

    def __init__(self,
                 resolutionManager,
                 entityDatabase,
                 mainWindow,
                 parent=None) -> None:

        super(ResolutionList, self).__init__(parent=parent)

        self.resolutionManager = resolutionManager
        self.lentDB = entityDatabase
        self.mainWindow = mainWindow
        self.setDragEnabled(True)
        self.setHeaderLabels(['Resolutions'])
        self.setAlternatingRowColors(False)
        self.setMinimumWidth(200)
        self.setSortingEnabled(True)
        self.sortByColumn(0, QtCore.Qt.SortOrder.AscendingOrder)

        self.loadAllResolutions()

    def loadAllResolutions(self) -> None:
        self.clear()
        for category in self.resolutionManager.getResolutionCategories():
            resTreeItem = QtWidgets.QTreeWidgetItem(self, [category])
            resolutions = self.resolutionManager.getResolutionsInCategory(category)
            for res in resolutions:
                ResolutionWidget(resTreeItem, text=res)

    def loadResolutionsForSelected(self, selected) -> None:
        self.clear()
        if len(selected) == 0:
            self.loadAllResolutions()
            return
        entityTypes = set()
        for item in selected:
            if not isinstance(item, BaseNode):
                continue
            ent = self.lentDB.getEntity(item.uid)
            entityTypes.add(ent['Entity Type'])
        res = self.resolutionManager.getResolutionsForEntityTypesByCategory(entityTypes)
        for category in res:
            resolutions = res[category]
            if len(resolutions) != 0:
                resTreeItem = QtWidgets.QTreeWidgetItem(self, [category])
                for resolution in resolutions:
                    ResolutionWidget(resTreeItem, text=resolution)

    def mouseDoubleClickEvent(self, event) -> None:
        super(ResolutionList, self).mouseDoubleClickEvent(event)
        resItem = self.itemAt(event.pos())
        if resItem is None or not isinstance(resItem, ResolutionWidget):
            return
        # Resolution Widgets should always have a parent, no need to check.
        category = resItem.parent().text(0)
        resolution = resItem.text(0)
        if resolution not in self.resolutionManager.getResolutionsInCategory(category):
            return

        self.mainWindow.runResolution(f'{category}/{resolution}')


class ResolutionWidget(QtWidgets.QTreeWidgetItem):

    def __init__(self, parent, icon=None, text="") -> None:
        super(ResolutionWidget, self).__init__(parent, [text])
        if icon is not None:
            self.setIcon(0, icon)


class NodeList(QtWidgets.QTreeWidget):

    def __init__(self, resourceHandler, parent=None) -> None:
        super(NodeList, self).__init__(parent=parent)

        self.resourceHandler = resourceHandler
        self.setDragEnabled(True)
        self.setHeaderLabels(['Entities'])
        self.setAlternatingRowColors(False)
        self.setSortingEnabled(True)
        self.sortByColumn(0, QtCore.Qt.SortOrder.AscendingOrder)
        self.allEntities = []

        self.loadEntities()

    def loadEntities(self) -> None:
        self.clear()
        self.allEntities = []
        for category in self.resourceHandler.getEntityCategories():
            catTreeItem = QtWidgets.QTreeWidgetItem(self, [category])
            entities = self.resourceHandler.getAllEntityDetailsWithIconsInCategory(
                category)
            for entity in entities:
                NodeWidget(catTreeItem,
                           QtGui.QIcon(entity[1]),
                           entity[0]['Entity Type'],
                           dumps(entity[0]))

        self.allEntities = self.resourceHandler.getAllEntities()

    def mouseMoveEvent(self, event) -> None:
        """
        Handle dragging of entities onto canvas.
        """
        if event.buttons() == QtCore.Qt.MouseButton.LeftButton:
            itemDragged = self.itemAt(event.pos())
            if itemDragged is None or \
                    itemDragged.text(0) not in self.allEntities:
                return

            self.setCurrentItem(itemDragged)
            drag = QtGui.QDrag(self)
            mimeData = QtCore.QMimeData()

            mimeData.setText(itemDragged.entityJsonText)
            drag.setMimeData(mimeData)

            # All Entities should have icons, but you never know.
            pixmap = None
            if itemDragged.icon(0) is not None:
                pixmap = itemDragged.icon(0).pixmap(40, 40)
                drag.setPixmap(pixmap)
            drag.setHotSpot(QtCore.QPoint(pixmap.rect().width() // 2, pixmap.rect().height() // 2))
            drag.exec_()


class NodeWidget(QtWidgets.QTreeWidgetItem):

    def __init__(self, parent, icon=None, name="", entityJsonText="") -> None:
        super(NodeWidget, self).__init__(parent, [name])
        if icon is not None:
            self.setIcon(0, icon)
        self.entityJsonText = entityJsonText
