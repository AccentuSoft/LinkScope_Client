#!/usr/bin/env python3

from PySide6 import QtWidgets, QtCore, QtGui
from Core.Interface import Stylesheets


class DockBarTwo(QtWidgets.QDockWidget):

    def initialiseLayout(self) -> None:
        childWidget = QtWidgets.QTabWidget()
        self.setWidget(childWidget)
        scrollAreaWidget = QtWidgets.QScrollArea()

        scrollAreaWidget.setWidget(self.entDetails)
        scrollAreaWidget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        childWidget.addTab(scrollAreaWidget, 'Entity Details')
        childWidget.addTab(self.oracle, 'Oracle')
        self.setMaximumWidth(500)
        self.resize(self.height(), 500)

    def __init__(self,
                 mainWindow,
                 resourceHandler,
                 entityDB,
                 title="DockBar Two"):
        super(DockBarTwo, self).__init__(parent=mainWindow)

        self.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea |
                             QtCore.Qt.RightDockWidgetArea)
        self.setFeatures(QtWidgets.QDockWidget.DockWidgetMovable |
                         QtWidgets.QDockWidget.DockWidgetFloatable |
                         QtWidgets.QDockWidget.DockWidgetClosable)
        self.setWindowTitle(title)
        self.resourceHandler = resourceHandler
        self.entityDB = entityDB
        self.setObjectName(title)

        self.oracle = Oracle(self.parent(), self)
        self.entDetails = EntityDetails(self.resourceHandler,
                                        self.entityDB,
                                        self.parent(),
                                        self)

        self.initialiseLayout()


class EntityDetails(QtWidgets.QWidget):
    """
    This class is used to display a detailed view of the attributes of
    the selected entity / entities.
    """

    def __init__(self,
                 resourceHandler,
                 entityDB,
                 mainWindow,
                 parent=None):

        super(EntityDetails, self).__init__(parent=parent)

        self.mainWindow = mainWindow
        self.resourceHandler = resourceHandler
        self.entityDB = entityDB
        self.detailsLayout = QtWidgets.QStackedLayout()
        self.setLayout(self.detailsLayout)

        layoutNothingSelected = QtWidgets.QGridLayout()
        widgetNothing = QtWidgets.QWidget()
        widgetNothing.setLayout(layoutNothingSelected)
        self.detailsLayout.addWidget(widgetNothing)

        layoutOneNodeSelected = QtWidgets.QGridLayout()
        widgetOneNode = QtWidgets.QWidget()
        widgetOneNode.setLayout(layoutOneNodeSelected)
        self.detailsLayout.addWidget(widgetOneNode)

        layoutMultipleItemsSelected = QtWidgets.QGridLayout()
        widgetMultiItems = QtWidgets.QWidget()
        widgetMultiItems.setLayout(layoutMultipleItemsSelected)
        self.detailsLayout.addWidget(widgetMultiItems)

        # Need to keep track of how many nodes are selected.
        # ~ Nothing Selected/Hovered Layout
        nothingLabel = QtWidgets.QLabel("Nothing is Selected.")
        nothingLabel.setAlignment(QtCore.Qt.AlignHCenter |
                                  QtCore.Qt.AlignVCenter)
        layoutNothingSelected.addWidget(nothingLabel)
        ###

        # ~ One Link/Node Selected/Hovered Layout
        # ~~ Part 1
        summaryLayout = QtWidgets.QGridLayout()
        summaryPanel = QtWidgets.QWidget()
        summaryPanel.setLayout(summaryLayout)
        self.summaryIcon = QtWidgets.QLabel("")  # QtGui.QIcon(None)
        self.entityTypeLabel = QtWidgets.QLabel("")
        self.entityUIDLabel = QtWidgets.QLabel("")
        self.entityPrimaryLabel = QtWidgets.QLabel("")
        summaryLayout.addWidget(self.summaryIcon, 0, 0)
        summaryLayout.addWidget(self.entityTypeLabel, 0, 1, 1, 3)
        summaryLayout.addWidget(self.entityPrimaryLabel, 1, 1)
        summaryLayout.addWidget(self.entityUIDLabel, 2, 1)
        layoutOneNodeSelected.addWidget(summaryPanel, 0, 0)

        # ~~ Part 2
        self.nodeLinkL = QtWidgets.QStackedLayout()
        nodeLinkSwitcher = QtWidgets.QWidget()
        nodeLinkSwitcher.setLayout(self.nodeLinkL)
        layoutOneNodeSelected.addWidget(nodeLinkSwitcher, 1, 0)

        relationshipsLayout = QtWidgets.QGridLayout()
        relationshipsPanel = QtWidgets.QWidget()
        relationshipsPanel.setLayout(relationshipsLayout)
        self.relationshipsIncomingTable = RelationshipsTable(self, mainWindow, uidLabel=self.entityPrimaryLabel,
                                                             incomingOrOutgoing=0)
        self.relationshipsOutgoingTable = RelationshipsTable(self, mainWindow, uidLabel=self.entityPrimaryLabel,
                                                             incomingOrOutgoing=1)
        self.relationshipsIncomingTable.setHeaderLabel('Incoming Links')
        self.relationshipsOutgoingTable.setHeaderLabel('Outgoing Links')
        relationshipsLayout.addWidget(self.relationshipsIncomingTable, 0, 0)
        relationshipsLayout.addWidget(self.relationshipsOutgoingTable, 1, 0)
        self.nodeLinkL.addWidget(relationshipsPanel)

        oneLinkRelLayout = QtWidgets.QHBoxLayout()
        oneLinkRelPanel = QtWidgets.QWidget()
        oneLinkRelPanel.setMaximumHeight(150)
        oneLinkRelPanel.setLayout(oneLinkRelLayout)
        self.linkParent = SingleLinkItem(self, mainWindow)  # QtWidgets.QLabel("")
        self.linkParent.setStyleSheet(Stylesheets.DOCK_BAR_TWO_LINK)
        self.linkIcon = QtWidgets.QLabel("")
        self.linkIcon.setMaximumHeight(90)
        self.linkIcon.setStyleSheet(Stylesheets.DOCK_BAR_TWO_LINK)
        self.linkIcon.setAlignment(QtCore.Qt.AlignCenter)
        self.linkChild = SingleLinkItem(self, mainWindow)  # QtWidgets.QLabel("")
        self.linkChild.setStyleSheet(Stylesheets.DOCK_BAR_TWO_LINK)
        oneLinkRelLayout.addWidget(self.linkParent)
        oneLinkRelLayout.addWidget(self.linkIcon)
        oneLinkRelLayout.addWidget(self.linkChild)
        self.nodeLinkL.addWidget(oneLinkRelPanel)

        # ~~ Part 3
        scroll = QtWidgets.QScrollArea()

        self.detailsLayoutOneNode = QtWidgets.QFormLayout()
        detailsLayoutOneNodePanel = QtWidgets.QWidget()
        detailsLayoutOneNodePanel.setLayout(self.detailsLayoutOneNode)
        scroll.setWidget(detailsLayoutOneNodePanel)
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(200)
        # scroll.setMaximumHeight(400)
        layoutOneNodeSelected.addWidget(scroll, 2, 0)

        # ~ Multiple Links/Nodes Selected Layout
        self.nodesTable = RelationshipsTable(self, mainWindow)
        self.nodesTable.setMaximumHeight(300)
        self.nodesTable.setHeaderLabels(["Entity", "Incoming Links", "Outgoing Links"])
        self.linksTable = LinksTable(self, mainWindow)
        self.linksTable.setMaximumHeight(300)
        self.linksTable.setHeaderLabels(["Resolution", "Parent", "Child"])
        multiNodesTableLabelOne = QtWidgets.QLabel("Selected Nodes:")
        layoutMultipleItemsSelected.addWidget(multiNodesTableLabelOne, 0, 0)
        layoutMultipleItemsSelected.addWidget(self.nodesTable, 1, 0)
        multiNodesTableLabelTwo = QtWidgets.QLabel("Selected Links:")
        layoutMultipleItemsSelected.addWidget(multiNodesTableLabelTwo, 2, 0)
        layoutMultipleItemsSelected.addWidget(self.linksTable, 3, 0)

        self.setMinimumWidth(475)
        self.setMaximumWidth(475)
        self.setMaximumHeight(550)

        self.currentlyShown = []

    def displayWidgetDetails(self, jsonDicts) -> None:
        """
        jsonDicts: a list of json strings, each representing
                   an entity or link.
        isNode: Whether the json string(s) is/are nodes or links.
        """
        if jsonDicts == self.currentlyShown:
            return
        self.currentlyShown = jsonDicts
        numberOfItems = len(jsonDicts)
        if numberOfItems == 0:
            self.layout().setCurrentIndex(0)
            return
        if None in jsonDicts:
            self.mainWindow.MESSAGEHANDLER.error('Received None value when trying to display widget details.',
                                                 popUp=False)
            return
        self.clearDetailsHelper()
        isNode = None
        if numberOfItems == 1:
            entity = jsonDicts[0]
            isNode = self.entityDB.isNode(entity['uid'])
            self.populateOneSummaryHelper(entity, isNode)
            self.populateOneDetailsHelper(entity)
            if isNode:
                self.populateOneRelationshipHelper(entity['uid'])
            else:
                self.populateOneLinkRelationshipHelper(entity['uid'])
        else:
            for item in jsonDicts:
                if item.get('Entity Type') is not None:
                    self.populateMultiRelationshipHelperNode(item)
                else:
                    self.populateMultiRelationshipHelperLink(item)
        self.switchLayoutHelper(numberOfItems, isNode)

    # Display helper functions
    def clearDetailsHelper(self) -> None:
        """
        Clear tree widget items from tree widgets.
        """
        rows = self.detailsLayoutOneNode.rowCount()
        for row in range(rows):
            self.detailsLayoutOneNode.removeRow(0)
        self.relationshipsIncomingTable.clear()
        self.relationshipsOutgoingTable.clear()
        self.nodesTable.clear()
        self.linksTable.clear()

    def populateOneDetailsHelper(self, jsonDict) -> None:
        if jsonDict is None or jsonDict == []:
            return
        for key in jsonDict:
            if key == "uid" or key == "Child UIDs" or key == "Icon":
                continue
            elif key == "Notes":
                notesTextArea = QtWidgets.QPlainTextEdit(jsonDict[key])
                notesTextArea.setReadOnly(True)
                self.detailsLayoutOneNode.addRow(key, notesTextArea)
            else:
                self.detailsLayoutOneNode.addRow(key, QtWidgets.QLabel(str(jsonDict[key])))

    def populateOneLinkRelationshipHelper(self, uid) -> None:
        first = uid[0]
        firstJson = self.entityDB.getEntity(first)
        second = uid[1]
        secondJson = self.entityDB.getEntity(second)
        firstPixmap = QtGui.QPixmap()
        firstPixmap.loadFromData(firstJson.get('Icon'))
        secondPixmap = QtGui.QPixmap()
        secondPixmap.loadFromData(secondJson.get('Icon'))
        self.linkParent.linkItemPic.setPixmap(firstPixmap)
        self.linkParent.linkItemName.setText(firstJson[list(firstJson)[1]])
        self.linkParent.linkItemUid = firstJson['uid']
        self.linkChild.linkItemPic.setPixmap(secondPixmap)
        self.linkChild.linkItemName.setText(secondJson[list(secondJson)[1]])
        self.linkChild.linkItemUid = secondJson['uid']

    def populateOneRelationshipHelper(self, uid) -> None:
        inc = self.entityDB.getIncomingLinks(uid)
        out = self.entityDB.getOutgoingLinks(uid)
        for edge in inc:
            uid = edge[0]
            edgeJson = self.entityDB.getEntity(uid)
            nodePixmap = QtGui.QPixmap()
            nodePixmap.loadFromData(edgeJson.get('Icon'))
            ResolutionTreeWidgetEntity(self.relationshipsIncomingTable,
                                       nodePixmap,
                                       edgeJson[list(edgeJson)[1]],
                                       uid)
        for edge in out:
            uid = edge[1]
            edgeJson = self.entityDB.getEntity(uid)
            nodePixmap = QtGui.QPixmap()
            nodePixmap.loadFromData(edgeJson.get('Icon'))
            ResolutionTreeWidgetEntity(self.relationshipsOutgoingTable,
                                       nodePixmap,
                                       edgeJson[list(edgeJson)[1]],
                                       uid)

    def populateMultiRelationshipHelperNode(self, nodeJson) -> None:
        inc = len(self.entityDB.getIncomingLinks(nodeJson['uid']))
        out = len(self.entityDB.getOutgoingLinks(nodeJson['uid']))
        nodePixmap = QtGui.QPixmap()
        nodePixmap.loadFromData(nodeJson.get('Icon'))
        ResolutionTreeWidgetEntity(self.nodesTable,
                                   nodePixmap,
                                   nodeJson[list(nodeJson)[1]],
                                   nodeJson['uid'],
                                   inc,
                                   out)

    def populateMultiRelationshipHelperLink(self, linkJson) -> None:
        uid = linkJson['uid']
        parent = self.entityDB.getEntity(uid[0])
        child = self.entityDB.getEntity(uid[1])
        LinksTreeWidgetEntity(self.linksTable,
                              QtGui.QPixmap(self.resourceHandler.getLinkPicture()),
                              linkJson['Resolution'],
                              parent[list(parent)[1]],
                              child[list(child)[1]],
                              uid)

    def populateOneSummaryHelper(self, jsonDict, isNode) -> None:
        if isNode:
            self.entityUIDLabel.setText(str(jsonDict[list(jsonDict)[1]]))
            self.entityPrimaryLabel.setText(jsonDict[list(jsonDict)[0]])
            self.entityTypeLabel.setText(jsonDict['Entity Type'])
            summaryPixmap = QtGui.QPixmap()
            summaryPixmap.loadFromData(jsonDict.get('Icon'))
            self.summaryIcon.setPixmap(summaryPixmap)
        else:
            self.entityUIDLabel.setText("--")
            self.entityPrimaryLabel.setText(jsonDict['Resolution'])
            self.entityTypeLabel.setText('Resolution')
            self.summaryIcon.setPixmap(QtGui.QPixmap(
                self.resourceHandler.getLinkPicture()))
            self.linkIcon.setPixmap(QtGui.QPixmap(
                self.resourceHandler.getLinkArrowPicture()))

    def switchLayoutHelper(self, selectionCount, isNode) -> None:
        """
        Switches between showing nothing, showing details for 1 node/link
           and showing details for multiple nodes/links
        Layout 0 = Nothing
        Layout 1 = 1 node / link
        Layout 2 = multi nodes / links
        """
        # selectionCount should never be 0, it is checked before this function is called
        if selectionCount == 1:
            if isNode:
                self.detailsLayout.setCurrentIndex(1)
                self.nodeLinkL.setCurrentIndex(0)
            else:
                self.detailsLayout.setCurrentIndex(1)
                self.nodeLinkL.setCurrentIndex(1)
        else:
            self.detailsLayout.setCurrentIndex(2)


class SingleLinkItem(QtWidgets.QWidget):

    def __init__(self, parent, mainWindow):
        super().__init__(parent=parent)

        self.linkItemPic = QtWidgets.QLabel()
        
        self.linkItemPic.setAlignment(QtCore.Qt.AlignCenter)
        self.linkItemName = QtWidgets.QLabel()
        
        self.linkItemName.setAlignment(QtCore.Qt.AlignCenter)
        self.linkItemUid = ""
        self.setMaximumHeight(90)

        linkItemLayout = QtWidgets.QVBoxLayout()
        self.setLayout(linkItemLayout)
        linkItemLayout.addWidget(self.linkItemPic)
        linkItemLayout.addWidget(self.linkItemName)
        self.mainWindow = mainWindow

    def mousePressEvent(self, event):
        """
        Have the canvas select the clicked item.
        """
        self.mainWindow.setCurrentCanvasSelection([self.linkItemUid])
        super().mousePressEvent(event)


class RelationshipsTable(QtWidgets.QTreeWidget):

    def __init__(self, parent, mainWindow, uidLabel: QtWidgets.QLabel = None, incomingOrOutgoing: int = None):
        super().__init__(parent=parent)
        self.mainWindow = mainWindow
        self.incomingOrOutgoing = incomingOrOutgoing
        self.uidLabel = uidLabel

    def mousePressEvent(self, event):
        """
        Have the canvas select the clicked item.
        """
        # The super() call is not technically needed.
        super().mousePressEvent(event)
        if event.button() == QtGui.Qt.MouseButton.LeftButton:
            itemClicked = self.itemAt(event.pos())
            if itemClicked is None:
                return
            if self.uidLabel is not None:
                potentialSelectedEntityUID = self.uidLabel.text()
                if potentialSelectedEntityUID == "":
                    self.mainWindow.setCurrentCanvasSelection([itemClicked.entityUID])
                elif self.incomingOrOutgoing is not None:
                    if self.incomingOrOutgoing == 0:
                        self.mainWindow.setCurrentCanvasSelection([(itemClicked.entityUID, potentialSelectedEntityUID)])
                    else:
                        self.mainWindow.setCurrentCanvasSelection([(potentialSelectedEntityUID, itemClicked.entityUID)])
            else:
                self.mainWindow.setCurrentCanvasSelection([itemClicked.entityUID])


class LinksTable(QtWidgets.QTreeWidget):

    def __init__(self, parent, mainWindow):
        super().__init__(parent=parent)
        self.mainWindow = mainWindow

    def mousePressEvent(self, event):
        """
        Have the canvas select the clicked item.
        """
        if event.button() == QtGui.Qt.MouseButton.LeftButton:
            itemClicked = self.itemAt(event.pos())
            if itemClicked is None:
                return
            self.mainWindow.setCurrentCanvasSelection([itemClicked.uid])
        else:
            super().mousePressEvent(event)


class LinksTreeWidgetEntity(QtWidgets.QTreeWidgetItem):
    def __init__(self,
                 parent,
                 icon=None,
                 resolutionText=None,
                 ent1=None,
                 ent2=None,
                 uid=None):
        super().__init__(parent)

        self.setText(0, resolutionText)
        self.setText(1, str(ent1))
        self.setText(2, str(ent2))
        self.uid = uid
        self.setIcon(0, icon)
        self.setIcon(1, icon)


class ResolutionTreeWidgetEntity(QtWidgets.QTreeWidgetItem):
    def __init__(self,
                 parent,
                 icon=None,
                 name="",
                 entityUID=None,
                 relInc=None,
                 relOut=None):

        super().__init__(parent, [name])
        if icon is not None:
            self.setIcon(0, icon)
        if relInc is not None:
            self.setText(1, str(relInc))
        if relOut is not None:
            self.setText(2, str(relOut))
        self.entityUID = entityUID


class Oracle(QtWidgets.QWidget):
    """
    This class is used to query the Question Answering AI model.
    It will be fed data from the files the user imports into
      the software.
    """

    def __init__(self, mainWindow, parent=None):
        super(Oracle, self).__init__(parent=parent)

        self.mainWindow = mainWindow
        oracleLayout = QtWidgets.QGridLayout()
        self.setLayout(oracleLayout)

        self.answerLabel = QtWidgets.QLabel("Answer Section")
        self.answerLabel.setStyleSheet(Stylesheets.DOCK_BAR_LABEL)
        self.answerLabel.setAlignment(QtCore.Qt.AlignHCenter |
                                      QtCore.Qt.AlignVCenter)
        oracleLayout.addWidget(self.answerLabel, 1, 0, 1, 2)
        self.answerSection = QtWidgets.QPlainTextEdit()
        self.answerSection.setReadOnly(True)
        self.answerSection.setPlaceholderText(
            "The answer to your Question will appear here.")
        self.answerSection.setUndoRedoEnabled(False)
        oracleLayout.addWidget(self.answerSection, 2, 0, 1, 2)

        self.questionLabel = QtWidgets.QLabel("Ask a Question")
        self.questionLabel.setStyleSheet(Stylesheets.DOCK_BAR_LABEL)
        self.questionLabel.setAlignment(QtCore.Qt.AlignHCenter |
                                        QtCore.Qt.AlignVCenter)
        oracleLayout.addWidget(self.questionLabel, 3, 0, 1, 2)
        self.questionSection = QtWidgets.QLineEdit()
        self.questionSection.setPlaceholderText("Ask a Question here.")

        oracleLayout.addWidget(self.questionSection, 4, 0)

        self.submitQuestionButton = QtWidgets.QPushButton("Ask")
        oracleLayout.addWidget(self.submitQuestionButton, 4, 1)
        self.questionSection.setMinimumWidth(200)

        self.submitQuestionButton.clicked.connect(mainWindow.askQuestion)
