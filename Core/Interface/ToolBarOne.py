#!/usr/bin/env python3

from PySide6 import QtWidgets, QtGui
from Core.Interface import Stylesheets


class ToolBarOne(QtWidgets.QToolBar):

    def __init__(self, title, parent):
        # Parent is (expected to be) mainWindow.
        super().__init__(title, parent=parent)
        self.setObjectName(title)
        self.setToolButtonStyle(QtGui.Qt.ToolButtonTextUnderIcon)
        self.setStyleSheet(Stylesheets.TOOLBAR_STYLESHEET)

        newCanvas = QtGui.QAction("Add Canvas",
                                  self,
                                  statusTip="Create new Canvas or Open existing Canvas",
                                  triggered=self.addCanvas,
                                  icon=QtGui.QIcon(self.parent().RESOURCEHANDLER.getIcon('addCanvas')))
        self.addAction(newCanvas)
        self.insertSeparator(newCanvas)

        manualLink = QtGui.QAction('Create Manual &Link',
                                   self,
                                   statusTip="Link two entities together manually",
                                   triggered=self.createManualLink,
                                   icon=QtGui.QIcon(self.parent().RESOURCEHANDLER.getIcon('drawLink')))
        self.addAction(manualLink)
        self.insertSeparator(manualLink)

        uploadSelected = QtGui.QAction('Upload Selected Files',
                                       self,
                                       statusTip="Upload the selected file entities to the server",
                                       triggered=self.uploadSelectedFiles,
                                       icon=QtGui.QIcon(self.parent().RESOURCEHANDLER.getIcon('uploading')))
        self.addAction(uploadSelected)
        self.insertSeparator(uploadSelected)

        selectLeaves = QtGui.QAction('Select Leaf Nodes',
                                     self,
                                     statusTip="Select nodes with one or more incoming links and no outgoing links.",
                                     triggered=self.selectLeafNodes,
                                     icon=QtGui.QIcon(self.parent().RESOURCEHANDLER.getIcon('leafNodes')))
        self.addAction(selectLeaves)
        self.insertSeparator(selectLeaves)

        selectRoots = QtGui.QAction('Select Root Nodes',
                                    self,
                                    statusTip="Select nodes with one or more outgoing links and no incoming links.",
                                    triggered=self.selectRootNodes,
                                    icon=QtGui.QIcon(self.parent().RESOURCEHANDLER.getIcon('rootNodes')))
        self.addAction(selectRoots)
        self.insertSeparator(selectRoots)

        selectIsolated = QtGui.QAction('Select Isolated Nodes',
                                       self,
                                       statusTip="Select nodes with no incoming or outgoing links.",
                                       triggered=self.selectIsolatedNodes,
                                       icon=QtGui.QIcon(self.parent().RESOURCEHANDLER.getIcon('isolatedNodes')))
        self.addAction(selectIsolated)
        self.insertSeparator(selectIsolated)

        selectNonIsolated = QtGui.QAction('Select Non Isolated Nodes',
                                          self,
                                          statusTip="Select nodes with at least one incoming or outgoing link.",
                                          triggered=self.selectNonIsolatedNodes,
                                          icon=QtGui.QIcon(self.parent().RESOURCEHANDLER.getIcon('nonIsolatedNodes')))
        self.addAction(selectNonIsolated)
        self.insertSeparator(selectNonIsolated)

        shortestPath = QtGui.QAction('Find Shortest Path',
                                     self,
                                     statusTip="Find the shortest path (if any) between two selected entities.",
                                     triggered=self.findShortestPath,
                                     icon=QtGui.QIcon(self.parent().RESOURCEHANDLER.getIcon('shortestPath')))
        self.addAction(shortestPath)
        self.insertSeparator(shortestPath)
        mergeEntities = QtGui.QAction('Merge Entities',
                                      self,
                                      statusTip="Merge the selected entities into one.",
                                      triggered=self.mergeEntities,
                                      icon=QtGui.QIcon(self.parent().RESOURCEHANDLER.getIcon('merge')))
        self.addAction(mergeEntities)
        self.insertSeparator(mergeEntities)

        splitEntity = QtGui.QAction('Split Entity',
                                    self,
                                    statusTip="Split the selected entity into multiple different ones.",
                                    triggered=self.splitEntity,
                                    icon=QtGui.QIcon(self.parent().RESOURCEHANDLER.getIcon('split')))
        self.addAction(splitEntity)
        self.insertSeparator(splitEntity)

        generateReport = QtGui.QAction('Generate Report',
                                       self,
                                       statusTip="Generate Report of selected entities.",
                                       triggered=self.generateReports,
                                       icon=QtGui.QIcon(self.parent().RESOURCEHANDLER.getIcon('generateReport')))
        self.addAction(generateReport)
        self.insertSeparator(generateReport)

        rearrangeCanvas = QtGui.QAction('Rearrange Canvas',
                                        self,
                                        statusTip="Rearrange Canvas Nodes automatically.",
                                        triggered=self.rearrangeGraph,
                                        icon=QtGui.QIcon(self.parent().RESOURCEHANDLER.getIcon('rearrange')))
        self.addAction(rearrangeCanvas)
        self.insertSeparator(rearrangeCanvas)

        self.linkItems = []
        self.selectMode = False

    def createManualLink(self):
        self.parent().toggleLinkingMode()

    def rearrangeGraph(self):
        self.parent().centralWidget().tabbedPane.getCurrentScene().rearrangeGraph()

    def addCanvas(self):
        self.parent().addCanvas()

    def configureProxySettings(self):
        pass

    ###
    def publishCanvas(self):
        pass

    ###
    def selectLeafNodes(self):
        self.parent().selectLeafNodes()

    def selectRootNodes(self):
        self.parent().selectRootNodes()

    def selectIsolatedNodes(self):
        self.parent().selectIsolatedNodes()

    def selectNonIsolatedNodes(self):
        self.parent().selectNonIsolatedNodes()

    def findShortestPath(self):
        self.parent().findShortestPath()

    def uploadSelectedFiles(self):
        self.parent().uploadFiles()

    def downloadSelectedFiles(self):
        self.parent().downloadFile()

    def mergeEntities(self):
        self.parent().mergeEntities()

    def splitEntity(self):
        self.parent().splitEntity()

    def generateReports(self):
        self.parent().generateReport()
