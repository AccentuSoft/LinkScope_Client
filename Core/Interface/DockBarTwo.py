#!/usr/bin/env python3

from pathlib import Path
import magic
from PySide6 import QtWidgets, QtCore, QtGui
from Core.ResourceHandler import MinSizeStackedLayout, RichNotesEditor, resizePictureFromBuffer
from Core.GlobalVariables import hidden_fields_dockbars


class DockBarTwo(QtWidgets.QDockWidget):

    def initialiseLayout(self) -> None:
        childWidget = QtWidgets.QTabWidget()
        self.setWidget(childWidget)
        scrollAreaWidget = QtWidgets.QScrollArea()

        scrollAreaWidget.setWidget(self.entDetails)
        scrollAreaWidget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scrollAreaWidget.setWidgetResizable(True)
        scrollAreaWidget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum)

        childWidget.addTab(scrollAreaWidget, 'Entity Details')
        childWidget.addTab(self.oracle, 'Oracle')
        childWidget.addTab(self.tabNotes, 'Notes')

    def __init__(self,
                 mainWindow,
                 resourceHandler,
                 entityDB,
                 title="DockBar Two"):
        super(DockBarTwo, self).__init__(parent=mainWindow)

        self.setAllowedAreas(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea |
                             QtCore.Qt.DockWidgetArea.RightDockWidgetArea)
        self.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable |
                         QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable |
                         QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.setWindowTitle(title)
        self.resourceHandler = resourceHandler
        self.entityDB = entityDB
        self.setObjectName(title)

        self.oracle = Oracle(self.parent(), self)
        self.entDetails = EntityDetails(self.resourceHandler,
                                        self.entityDB,
                                        self.parent(),
                                        self)
        self.tabNotes = TabNotesPanel(self)

        self.initialiseLayout()

    def setNotesText(self, newText: str) -> None:
        if not self.tabNotes.textEditor.isReadOnly():
            self.tabNotes.textEditor.setReadOnly(True)
        self.tabNotes.textEditor.contents = newText
        self.tabNotes.textEditor.setMarkdown(newText)

    def getNotesText(self) -> str:
        """
        Get text with the Markdown control characters.
        @return:
        """
        return self.tabNotes.textEditor.toMarkdown()


class TabNotesPanel(QtWidgets.QWidget):
    """
    This class is used to allow the user to take notes on a tab by tab
    basis.
    """

    def __init__(self, parent=None):
        super(TabNotesPanel, self).__init__(parent=parent)
        tabNotesLayout = QtWidgets.QVBoxLayout()

        self.textEditor = RichNotesEditor(self)

        tabNotesLayout.addWidget(self.textEditor)
        self.setLayout(tabNotesLayout)


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
        self.detailsLayout = MinSizeStackedLayout()
        self.setLayout(self.detailsLayout)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum)

        layoutNothingSelected = QtWidgets.QVBoxLayout()
        widgetNothing = QtWidgets.QWidget()
        widgetNothing.setLayout(layoutNothingSelected)
        self.detailsLayout.addWidget(widgetNothing)

        layoutOneNodeSelected = QtWidgets.QVBoxLayout()
        widgetOneNode = QtWidgets.QWidget()
        widgetOneNode.setLayout(layoutOneNodeSelected)
        self.detailsLayout.addWidget(widgetOneNode)

        layoutMultipleItemsSelected = QtWidgets.QVBoxLayout()
        widgetMultiItems = QtWidgets.QWidget()
        widgetMultiItems.setLayout(layoutMultipleItemsSelected)
        self.detailsLayout.addWidget(widgetMultiItems)

        # Need to keep track of how many nodes are selected.
        # ~ Nothing Selected/Hovered Layout
        nothingLabel = QtWidgets.QLabel("Nothing is Selected.")
        nothingLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layoutNothingSelected.addWidget(nothingLabel)
        ###

        # ~ One Link/Node Selected/Hovered Layout
        # ~~ Part 1
        summaryLayout = QtWidgets.QGridLayout()
        summaryPanel = QtWidgets.QWidget()
        summaryPanel.setLayout(summaryLayout)
        self.summaryIcon = QtWidgets.QLabel("")
        self.summaryIcon.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum)
        self.entityTypeLabel = QtWidgets.QLabel("")
        self.entityUIDLabel = QtWidgets.QLineEdit("")
        self.entityUIDLabel.setReadOnly(True)
        self.entityPrimaryLabel = QtWidgets.QLineEdit("")
        self.entityPrimaryLabel.setReadOnly(True)
        summaryLayout.addWidget(self.summaryIcon, 0, 0)
        summaryLayout.addWidget(self.entityTypeLabel, 0, 1, 1, 3)
        summaryLayout.addWidget(self.entityPrimaryLabel, 1, 1)
        summaryLayout.addWidget(self.entityUIDLabel, 2, 1)
        layoutOneNodeSelected.addWidget(summaryPanel, 1)

        # ~~ Part 2
        self.nodeLinkL = QtWidgets.QStackedLayout()
        nodeLinkSwitcher = QtWidgets.QWidget()
        nodeLinkSwitcher.setLayout(self.nodeLinkL)
        layoutOneNodeSelected.addWidget(nodeLinkSwitcher, 1)

        relationshipsLayout = QtWidgets.QVBoxLayout()
        relationshipsPanel = QtWidgets.QWidget()
        relationshipsPanel.setLayout(relationshipsLayout)
        self.relationshipsIncomingTable = RelationshipsTable(self, mainWindow, uidLabel=self.entityPrimaryLabel,
                                                             incomingOrOutgoing=0)
        self.relationshipsOutgoingTable = RelationshipsTable(self, mainWindow, uidLabel=self.entityPrimaryLabel,
                                                             incomingOrOutgoing=1)
        self.relationshipsIncomingTable.setHeaderLabel('Incoming Links')
        self.relationshipsOutgoingTable.setHeaderLabel('Outgoing Links')
        relationshipsLayout.addWidget(self.relationshipsIncomingTable)
        relationshipsLayout.addWidget(self.relationshipsOutgoingTable)
        self.nodeLinkL.addWidget(relationshipsPanel)
        self.relationshipsIncomingTable.setMinimumHeight(125)
        self.relationshipsOutgoingTable.setMinimumHeight(125)

        oneLinkRelLayout = QtWidgets.QHBoxLayout()
        oneLinkRelPanel = QtWidgets.QWidget()
        oneLinkRelPanel.setMaximumHeight(150)
        oneLinkRelPanel.setLayout(oneLinkRelLayout)
        self.linkParent = SingleLinkItem(self, mainWindow)
        self.linkIcon = QtWidgets.QLabel("")
        self.linkIcon.setMaximumHeight(90)
        self.linkIcon.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.linkChild = SingleLinkItem(self, mainWindow)
        oneLinkRelLayout.addWidget(self.linkParent)
        oneLinkRelLayout.addWidget(self.linkIcon)
        oneLinkRelLayout.addWidget(self.linkChild)
        self.nodeLinkL.addWidget(oneLinkRelPanel)

        # ~~ Part 3
        scroll = QtWidgets.QScrollArea()

        self.detailsLayoutOneNode = QtWidgets.QGridLayout()
        detailsLayoutOneNodePanel = QtWidgets.QWidget()
        detailsLayoutOneNodePanel.setLayout(self.detailsLayoutOneNode)
        scroll.setWidget(detailsLayoutOneNodePanel)
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(200)
        layoutOneNodeSelected.addWidget(scroll, 10)

        # ~ Multiple Links/Nodes Selected Layout
        self.nodesTable = RelationshipsTable(self, mainWindow)
        self.nodesTable.setMaximumHeight(500)
        self.nodesTable.setHeaderLabels(["Entity", "Incoming Links", "Outgoing Links"])
        self.linksTable = LinksTable(self, mainWindow)
        self.linksTable.setMaximumHeight(500)
        self.linksTable.setHeaderLabels(["Resolution", "Parent", "Child"])
        self.multiNodesTableLabelOne = QtWidgets.QLabel("Selected Nodes:")
        self.multiNodesTableLabelOne.setMaximumHeight(20)
        layoutMultipleItemsSelected.addWidget(self.multiNodesTableLabelOne)
        layoutMultipleItemsSelected.addWidget(self.nodesTable)
        self.multiNodesTableLabelTwo = QtWidgets.QLabel("Selected Links:")
        self.multiNodesTableLabelTwo.setMaximumHeight(20)
        layoutMultipleItemsSelected.addWidget(self.multiNodesTableLabelTwo)
        layoutMultipleItemsSelected.addWidget(self.linksTable)

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
            self.detailsLayout.setCurrentIndex(0)
            return
        if None in jsonDicts:
            self.mainWindow.MESSAGEHANDLER.error('Received None value when trying to display widget details.',
                                                 popUp=False)
            self.detailsLayout.setCurrentIndex(0)
            return
        self.clearDetailsHelper()
        isNode = None
        try:
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
                nodesNumber = 0
                linksNumber = 0
                for item in jsonDicts:
                    if isinstance(item['uid'], str):
                        self.populateMultiRelationshipHelperNode(item)
                        nodesNumber += 1
                    else:
                        self.populateMultiRelationshipHelperLink(item)
                        linksNumber += 1
                self.multiNodesTableLabelOne.setText(f'Selected Nodes:   {str(nodesNumber)}')
                self.multiNodesTableLabelTwo.setText(f'Selected Links:   {str(linksNumber)}')

            self.switchLayoutHelper(numberOfItems, isNode)
        except Exception as exc:
            # If an error is thrown at some point during the process, show the default nothing selected screen.
            self.detailsLayout.setCurrentIndex(0)
            self.mainWindow.MESSAGEHANDLER.error(f'Error occurred while trying to display the details of the selected '
                                                 f'nodes: {str(exc)}', popUp=False, exc_info=False)

    # Display helper functions
    def clearDetailsHelper(self) -> None:
        """
        Clear tree widget items from tree widgets.
        """
        itemToRemove = self.detailsLayoutOneNode.takeAt(0)
        while itemToRemove is not None:
            itemToRemove.widget().deleteLater()
            del itemToRemove
            itemToRemove = self.detailsLayoutOneNode.takeAt(0)

        self.relationshipsIncomingTable.clear()
        self.relationshipsOutgoingTable.clear()
        self.nodesTable.clear()
        self.linksTable.clear()

    def populateOneDetailsHelper(self, jsonDict) -> None:
        if jsonDict is None or jsonDict == []:
            return
        rowCount = 0
        for key in jsonDict:
            if key in hidden_fields_dockbars:
                continue
            elif key == "Notes":
                notesTextArea = RichNotesEditor(self, jsonDict[key], False)
                self.detailsLayoutOneNode.addWidget(QtWidgets.QLabel(key), rowCount, 0)
                self.detailsLayoutOneNode.addWidget(notesTextArea, rowCount, 1, 10, 1)
                rowCount += 9
            else:
                valueLabel = QtWidgets.QLineEdit(str(jsonDict[key]))
                valueLabel.setReadOnly(True)

                self.detailsLayoutOneNode.addWidget(QtWidgets.QLabel(key), rowCount, 0)
                self.detailsLayoutOneNode.addWidget(valueLabel, rowCount, 1)
            rowCount += 1
        filePath = jsonDict.get('File Path')
        if filePath is not None:
            fullFilePath = Path(self.mainWindow.SETTINGS.value('Project/FilesDir')) / filePath
            if fullFilePath.exists() and fullFilePath.is_file():
                magicType = magic.from_file(str(fullFilePath), mime=True)
                if magicType.split('/')[0] == 'image':
                    previewImage = QtGui.QImage(fullFilePath)
                    if previewImage.isNull():
                        # If launched from terminal, expect errors like the following to show up:
                        # qt.gui.imageio: QImageIOHandler: Rejecting image as it exceeds the current allocation
                        #   limit of 128 megabytes
                        # This is fine - we are handling this here, by having the label show text instead of a null
                        #   image.
                        previewLabel = QtWidgets.QLabel('Error Creating Image Preview.')
                    else:
                        previewPixmap = QtGui.QPixmap(previewImage)
                        previewLabel = QtWidgets.QLabel()
                        previewLabel.setPixmap(previewPixmap.scaled(250,
                                                                    250,
                                                                    QtCore.Qt.AspectRatioMode.KeepAspectRatio))
                    self.detailsLayoutOneNode.addWidget(QtWidgets.QLabel('Preview:'), rowCount, 0)
                    self.detailsLayoutOneNode.addWidget(previewLabel, rowCount, 1, 10, 1)

    def populateOneLinkRelationshipHelper(self, uid) -> None:
        first = uid[0]
        firstJson = self.entityDB.getEntity(first)
        second = uid[1]
        secondJson = self.entityDB.getEntity(second)
        firstPixmap = QtGui.QPixmap()
        firstPixmap.loadFromData(resizePictureFromBuffer(firstJson.get('Icon'), (40, 40)))
        secondPixmap = QtGui.QPixmap()
        secondPixmap.loadFromData(resizePictureFromBuffer(secondJson.get('Icon'), (40, 40)))
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
            nodePixmap.loadFromData(resizePictureFromBuffer(edgeJson.get('Icon'), (40, 40)))
            ResolutionTreeWidgetEntity(self.relationshipsIncomingTable,
                                       nodePixmap,
                                       edgeJson[list(edgeJson)[1]],
                                       uid)
        self.relationshipsIncomingTable.setHeaderLabel(f'Incoming Links:   {len(inc)}')
        for edge in out:
            uid = edge[1]
            edgeJson = self.entityDB.getEntity(uid)
            nodePixmap = QtGui.QPixmap()
            nodePixmap.loadFromData(resizePictureFromBuffer(edgeJson.get('Icon'), (40, 40)))
            ResolutionTreeWidgetEntity(self.relationshipsOutgoingTable,
                                       nodePixmap,
                                       edgeJson[list(edgeJson)[1]],
                                       uid)
        self.relationshipsOutgoingTable.setHeaderLabel(f'Outgoing Links:   {len(out)}')

    def populateMultiRelationshipHelperNode(self, nodeJson) -> None:
        inc = len(self.entityDB.getIncomingLinks(nodeJson['uid']))
        out = len(self.entityDB.getOutgoingLinks(nodeJson['uid']))
        nodePixmap = QtGui.QPixmap()
        nodePixmap.loadFromData(resizePictureFromBuffer(nodeJson.get('Icon'), (40, 40)))
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
            summaryPixmap.loadFromData(resizePictureFromBuffer(jsonDict.get('Icon'), (40, 40)))
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

        self.linkItemPic.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.linkItemName = QtWidgets.QLineEdit()
        self.linkItemName.setReadOnly(True)

        self.linkItemName.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
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
        self.answerLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        oracleLayout.addWidget(self.answerLabel, 1, 0, 1, 2)
        self.answerSection = QtWidgets.QPlainTextEdit()
        self.answerSection.setReadOnly(True)
        self.answerSection.setPlaceholderText(
            "The answer to your Question will appear here.")
        self.answerSection.setUndoRedoEnabled(False)
        oracleLayout.addWidget(self.answerSection, 2, 0, 1, 2)

        self.questionLabel = QtWidgets.QLabel("Ask a Question")
        self.questionLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        oracleLayout.addWidget(self.questionLabel, 3, 0, 1, 2)
        self.questionSection = QtWidgets.QLineEdit()
        self.questionSection.setPlaceholderText("Ask a Question here.")

        oracleLayout.addWidget(self.questionSection, 4, 0)

        self.submitQuestionButton = QtWidgets.QPushButton("Ask")
        oracleLayout.addWidget(self.submitQuestionButton, 4, 1)
        self.questionSection.setMinimumWidth(200)

        self.submitQuestionButton.clicked.connect(mainWindow.askQuestion)
