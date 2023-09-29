#!/usr/bin/env python3

import contextlib
import csv
import statistics
import re
import networkx as nx
import string
from typing import Union, Optional, Any
from uuid import uuid4
from pathlib import Path

from PySide6 import QtWidgets, QtCore, QtCharts, QtGui
from Core.GlobalVariables import non_string_fields
from Core.ResourceHandler import resizePictureFromBuffer
from Core.PathHelper import is_path_exists_or_creatable_portable



class QueryBuilderWizard(QtWidgets.QDialog):

    def __init__(self, mainWindowObject):
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
            resizedIcon = resizePictureFromBuffer(nodeDetails['Icon'], (40, 40))
            pixmapIcon.loadFromData(resizedIcon)
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

    def __init__(self, mainWindowObject, entitiesDict: dict, selectedUIDs: set, selectedFields: set,
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


class LQLQueryBuilder:
    QUERIES_HISTORY = {}

    databaseSnapshot = None
    databaseEntities = None
    allCanvases = None
    canvasesEntitiesDict = None
    allEntityFields = None
    allEntitiesInit = None
    allEntities = None

    def __init__(self, mainWindow):
        self.mainWindow = mainWindow

    def takeSnapshot(self):
        with self.mainWindow.LENTDB.dbLock:
            # Create a copy
            self.databaseSnapshot = self.mainWindow.LENTDB.database.copy()

        self.databaseEntities = set(self.databaseSnapshot.nodes)

        self.allCanvases = self.getAllCanvasNames()
        self.canvasesEntitiesDict = self.getCanvasesEntitiesDict(self.allCanvases)
        self.allEntityFields, self.allEntitiesInit = self.getAllEntitiesAndFields()

        # Re-define database entities to remove Group Entities
        self.databaseEntities = set(self.allEntitiesInit.keys())

    def getAllEntitiesAndFields(self) -> (set, dict):
        entitiesSnapshot = {entity: self.databaseSnapshot.nodes[entity] for entity in self.databaseSnapshot.nodes
                            if self.databaseSnapshot.nodes[entity].get('Entity Type') != 'EntityGroup'}
        entityFields = set()
        for entityUID in entitiesSnapshot:
            entityFields.update(entitiesSnapshot[entityUID].keys())
        for field in non_string_fields:
            try:
                entityFields.remove(field)
            except KeyError:
                # This typically only happens if there are no entities in the database.
                continue
        return entityFields, entitiesSnapshot

    def getAllCanvasNames(self) -> list:
        canvasNames = list(self.mainWindow.centralWidget().tabbedPane.canvasTabs.keys())
        canvasNames.append('*')
        return canvasNames

    def getEntitiesOnCanvas(self, canvasName: str):
        try:
            # Ensure that we don't have nodes here that are not present in our database snapshot
            canvasNodes = set(
                self.mainWindow.centralWidget().tabbedPane.canvasTabs[canvasName].scene().sceneGraph.nodes)
            return canvasNodes.intersection(self.databaseEntities)
        except KeyError:
            return None

    def getCanvasesEntitiesDict(self, allCanvasNames: list):
        returnDict = {}
        for canvas in allCanvasNames:
            allEntitiesOnCanvas = self.getEntitiesOnCanvas(canvas)
            if allEntitiesOnCanvas is not None:
                returnDict[canvas] = allEntitiesOnCanvas
            else:
                returnDict[canvas] = set()

        return returnDict

    def parseSelect(self, selectClause: str, selectValue: Union[str, list]):
        if selectClause == 'SELECT':
            return self.allEntityFields if '*' in selectValue else \
                {entityField for entityField in selectValue if entityField in self.allEntityFields}

        try:
            clauseValue = re.compile(selectValue)
            return {entityField for entityField in self.allEntityFields if clauseValue.match(entityField)}
        except re.error:
            return set()

    def parseSource(self, sourceClause: str, sourceValues: Union[None, list], fieldsToSelect: set) -> set:
        """
        sourceValues:
        [[("AND" | "OR" | None), ("CANVAS" | "RCANVAS"), (True | False), <User Input>], ...]
        OR
        None
            if sourceClause == "FROMDB"
        """
        if sourceClause == "FROMDB":
            resultEntitySet = set(self.databaseEntities)
        else:
            resultEntitySet = set()
            for sourceValue in sourceValues:
                try:
                    if sourceValue[1] == "CANVAS":
                        if sourceValue[3] not in self.allCanvases:
                            raise ValueError('Reference to nonexistent canvas.')
                        matchingCanvases = [sourceValue[3]]
                    else:
                        canvasRegex = re.compile(sourceValue[3])
                        matchingCanvases = [canvasMatch for canvasMatch in self.allCanvases
                                            if canvasRegex.match(canvasMatch)]
                except (ValueError, re.error):
                    continue

                for matchingCanvas in matchingCanvases:
                    if sourceValue[0] == 'AND':
                        resultEntitySet = self.canvasAndNot(resultEntitySet, self.canvasesEntitiesDict[matchingCanvas]) \
                            if sourceValue[2] is True else \
                            self.canvasAnd(resultEntitySet, self.canvasesEntitiesDict[matchingCanvas])

                    elif sourceValue[2] is True:
                        resultEntitySet = self.canvasOrNot(resultEntitySet,
                                                           self.canvasesEntitiesDict[matchingCanvas],
                                                           self.databaseEntities)
                    else:
                        resultEntitySet = self.canvasOr(resultEntitySet,
                                                        self.canvasesEntitiesDict[matchingCanvas])

        # Filter out all entities that do not contain at least one of the selected fields.
        for entity in list(resultEntitySet):
            validEntity = any(field in self.allEntities[entity].keys() for field in fieldsToSelect)

            if not validEntity:
                resultEntitySet.remove(entity)
                self.allEntities.pop(entity)
        return resultEntitySet

    def parseConditions(self, mainWindow, conditionClauses: Union[None, list], entitiesPool) -> set:
        """
        conditionClauses:
        [[("AND" | "OR" | None), ("Value Condition" | "Graph Condition"), (True | False), conditionValue], ...]

        conditionValue:
            if Value Condition:
                [("ATTRIBUTE" | "RATTRIBUTE"), <User Input>,
                ("EQ" | "CONTAINS" | "STARTSWITH" | "ENDSWITH" | "RMATCH"), <User Input>]
            if Graph Condition:
                [("CHILDOF" <ENTITY> | "DESCENDANTOF " <ENTITY> |
                "PARENTOF" <ENTITY> | "ANCESTOROF " <ENTITY> |
                "NUMCHILDREN" (" < " | " <= " | " > " | " >= " | " == ") <DIGITS> |
                "NUMPARENTS" (" < " | " <= " | " > " | " >= " | " == ") <DIGITS> |
                "NUMANCESTORS" (" < " | " <= " | " > " | " >= " | " == ") <DIGITS> |
                "NUMDESCENDANTS" (" < " | " <= " | " > " | " >= " | " == ") <DIGITS> |
                "NUMIFIED_PARENTS_TOTAL" (" < " | " <= " | " > " | " >= " | " == ") <DIGITS> |
                "NUMIFIED_CHILDREN_TOTAL" (" < " | " <= " | " > " | " >= " | " == ") <DIGITS> |
                "CONNECTEDTO" <ENTITY> | "ISOLATED" | "ISROOT" | "ISLEAF")]
        """
        self.mainWindow = mainWindow
        self.allEntities = {uid: self.allEntities[uid] for uid in self.allEntities if uid in entitiesPool}
        uidsToSelect = set()

        for conditionClause in conditionClauses:
            isNot = conditionClause[2]
            conditionValue = conditionClause[3]
            try:
                userInput1 = conditionValue[1]
                userInput2 = conditionValue[3]
            except IndexError:
                # Not used in cases where a Graph Condition is specified
                userInput1 = None
                userInput2 = None
            firstArgument = conditionValue[0]
            if conditionClause[1] == "Value Condition":
                matchingFields = []
                if firstArgument == "ATTRIBUTE":
                    if userInput1 in self.allEntityFields:
                        matchingFields.append(userInput1)
                else:
                    try:
                        attributeRegex = re.compile(userInput1)
                    except re.error:
                        continue
                    matchingFields.extend(field for field in self.allEntityFields if attributeRegex.match(field))

                for matchingField in matchingFields:
                    entitiesToRemove = []
                    for entity in self.allEntities:
                        attributeKeyValue = str(self.allEntities[entity].get(matchingField))
                        if self.checkVCHelper(conditionValue[2], isNot, attributeKeyValue, userInput2):
                            uidsToSelect.add(entity)
                        elif conditionClause[0] == "AND":
                            entitiesToRemove.append(entity)
                    for entityToRemove in entitiesToRemove:
                        uidsToSelect.remove(entityToRemove)

            elif conditionClause[1] == "Graph Condition":
                entitiesToRemove = []
                for entity in self.allEntities:
                    if self.checkGCHelper(firstArgument, isNot, [entity] + conditionValue[1:]):
                        uidsToSelect.add(entity)
                    elif conditionClause[0] == "AND":
                        entitiesToRemove.append(entity)
                for entityToRemove in entitiesToRemove:
                    uidsToSelect.remove(entityToRemove)

        uidsToRemove = set(self.allEntities).difference(uidsToSelect)
        for entity in uidsToRemove:
            self.allEntities.pop(entity, None)

        return uidsToSelect

    def canvasOr(self, canvasSetA: set, canvasSetB: set):
        return canvasSetA.union(canvasSetB)

    def canvasAnd(self, canvasSetA: set, canvasSetB: set):
        return canvasSetA.intersection(canvasSetB)

    def canvasAndNot(self, canvasSetA: set, canvasSetB: set):
        return canvasSetA.difference(canvasSetB)

    def canvasOrNot(self, canvasSetA: set, canvasSetB: set, allEntitiesSet: set):
        return canvasSetA.union(allEntitiesSet.difference(canvasSetB))

    def checkEQ(self, valueA: str, valueB: str):
        return valueA == valueB

    def checkContains(self, valueA: str, valueB: str):
        return valueB in valueA

    def checkStartsWith(self, valueA: str, valueB: str):
        return valueA.startswith(valueB)

    def checkEndsWith(self, valueA: str, valueB: str):
        return valueA.endswith(valueB)

    def checkRMatch(self, valueA: str, valueB: str):
        with contextlib.suppress(re.error):
            valueMatch = re.compile(valueB)
            if valueMatch.match(valueA):
                return True
        return False

    def checkVCHelper(self, checkType: str, isNot: bool, valueA: str, valueB: str):
        returnVal = False
        if checkType == "CONTAINS":
            returnVal = self.checkContains(valueA, valueB)
        elif checkType == "ENDSWITH":
            returnVal = self.checkEndsWith(valueA, valueB)
        elif checkType == "EQ":
            returnVal = self.checkEQ(valueA, valueB)
        elif checkType == "RMATCH":
            returnVal = self.checkRMatch(valueA, valueB)
        elif checkType == "STARTSWITH":
            returnVal = self.checkStartsWith(valueA, valueB)
        return not returnVal if isNot else returnVal

    def checkParentOf(self, valueA: str, valueB: str):
        return self.databaseSnapshot.has_successor(valueA, valueB)

    def checkAncestorOf(self, valueA: str, valueB: str):
        with contextlib.suppress(nx.NetworkXError):
            if valueB in nx.descendants(self.databaseSnapshot, valueA):
                return True
        return False

    def checkChildOf(self, valueA: str, valueB: str):
        return self.databaseSnapshot.has_predecessor(valueA, valueB)

    def checkDescendantOf(self, valueA: str, valueB: str):
        with contextlib.suppress(nx.NetworkXError):
            if valueB in nx.ancestors(self.databaseSnapshot, valueA):
                return True
        return False

    def checkNumChildren(self, valueA: str, valueB: str, valueC: float):
        numChildren = len(list(self.databaseSnapshot.successors(valueA)))
        return (valueB == "<" and numChildren < valueC) or \
            (valueB == "<=" and numChildren <= valueC) or \
            (valueB == ">" and numChildren > valueC) or \
            (valueB == ">=" and numChildren >= valueC) or \
            (valueB == "==" and numChildren == valueC)

    def checkNumParents(self, valueA: str, valueB: str, valueC: float):
        numParents = len(list(self.databaseSnapshot.predecessors(valueA)))
        return (valueB == "<" and numParents < valueC) or \
            (valueB == "<=" and numParents <= valueC) or \
            (valueB == ">" and numParents > valueC) or \
            (valueB == ">=" and numParents >= valueC) or \
            (valueB == "==" and numParents == valueC)

    def checkNumAncestors(self, valueA: str, valueB: str, valueC: float):
        numAncestors = len(list(nx.ancestors(self.databaseSnapshot, valueA)))
        return (valueB == "<" and numAncestors < valueC) or \
            (valueB == "<=" and numAncestors <= valueC) or \
            (valueB == ">" and numAncestors > valueC) or \
            (valueB == ">=" and numAncestors >= valueC) or \
            (valueB == "==" and numAncestors == valueC)

    def checkNumDescendants(self, valueA: str, valueB: str, valueC: float):
        numDescendants = len(list(nx.descendants(self.databaseSnapshot, valueA)))
        return (valueB == "<" and numDescendants < valueC) or \
            (valueB == "<=" and numDescendants <= valueC) or \
            (valueB == ">" and numDescendants > valueC) or \
            (valueB == ">=" and numDescendants >= valueC) or \
            (valueB == "==" and numDescendants == valueC)

    def checkNumifiedParentsTotal(self, valueA: str, valueB: str, valueC: float):
        parents = self.databaseSnapshot.predecessors(valueA)
        total = 0.0
        for item in parents:
            primaryField = self.mainWindow.RESOURCEHANDLER.getPrimaryFieldForEntityType(
                self.databaseSnapshot.nodes[item]['Entity Type'])
            with contextlib.suppress(Exception):
                total += self.modifyNumify(self.databaseSnapshot.nodes[item][primaryField])

        return (valueB == "<" and total < valueC) or \
            (valueB == "<=" and total <= valueC) or \
            (valueB == ">" and total > valueC) or \
            (valueB == ">=" and total >= valueC) or \
            (valueB == "==" and total == valueC)

    def checkNumifiedChildrenTotal(self, valueA: str, valueB: str, valueC: float):
        children = self.databaseSnapshot.successors(valueA)
        total = 0.0
        for item in children:
            primaryField = self.mainWindow.RESOURCEHANDLER.getPrimaryFieldForEntityType(
                self.databaseSnapshot.nodes[item]['Entity Type'])
            with contextlib.suppress(Exception):
                total += self.modifyNumify(self.databaseSnapshot.nodes[item][primaryField])
        return (valueB == "<" and total < valueC) or \
            (valueB == "<=" and total <= valueC) or \
            (valueB == ">" and total > valueC) or \
            (valueB == ">=" and total >= valueC) or \
            (valueB == "==" and total == valueC)

    def checkConnectedTo(self, valueA: str, valueB: str):
        with contextlib.suppress(nx.NetworkXError):
            if nx.has_path(self.databaseSnapshot, valueA, valueB):
                return True
        return False

    def checkIsolated(self, valueA: str):
        with contextlib.suppress(nx.NetworkXError):
            if valueA in self.databaseSnapshot.nodes and nx.is_isolate(self.databaseSnapshot, valueA):
                return True
        return False

    def checkIsRoot(self, valueA: str):
        with contextlib.suppress(nx.NetworkXError):
            if len(self.databaseSnapshot.in_edges(valueA)) == 0:
                return True
        return False

    def checkIsLeaf(self, valueA: str):
        with contextlib.suppress(nx.NetworkXError):
            if len(self.databaseSnapshot.out_edges(valueA)) == 0:
                return True
        return False

    def checkGCHelper(self, checkType: str, isNot: bool, args: list):
        returnVal = False
        if checkType == "ANCESTOROF":
            returnVal = self.checkAncestorOf(*args)
        elif checkType == "CHILDOF":
            returnVal = self.checkChildOf(*args)
        elif checkType == "CONNECTEDTO":
            returnVal = self.checkConnectedTo(*args)
        elif checkType == "DESCENDANTOF":
            returnVal = self.checkDescendantOf(*args)
        elif checkType == "ISLEAF":
            returnVal = self.checkIsLeaf(*args)
        elif checkType == "ISOLATED":
            returnVal = self.checkIsolated(*args)
        elif checkType == "ISROOT":
            returnVal = self.checkIsRoot(*args)
        elif checkType == "NUMCHILDREN":
            returnVal = self.checkNumChildren(*args)
        elif checkType == "NUMPARENTS":
            returnVal = self.checkNumParents(*args)
        elif checkType == "NUMANCESTORS":
            returnVal = self.checkNumAncestors(*args)
        elif checkType == "NUMDESCENDANTS":
            returnVal = self.checkNumDescendants(*args)
        elif checkType == "NUMIFIED_PARENTS_TOTAL":
            returnVal = self.checkNumifiedParentsTotal(*args)
        elif checkType == "NUMIFIED_CHILDREN_TOTAL":
            returnVal = self.checkNumifiedChildrenTotal(*args)
        elif checkType == "PARENTOF":
            returnVal = self.checkParentOf(*args)
        return not returnVal if isNot else returnVal

    def modifyNumify(self, valueA: str) -> float:
        # Get the first number that shows up.
        tempString = valueA.replace(',', '.')  # Making sure that floats are expressed the right way.
        count = 0
        for c in tempString:
            if c not in string.digits:
                count += 1
            else:
                break

        count2 = 0
        for c in tempString[count:]:
            if c in string.digits or c == '.':
                count2 += 1
            else:
                break

        # If there are no numbers in the string, its numeric value is 0.
        try:
            floatValue = float(tempString[count:count + count2])
        except ValueError:
            floatValue = 0.0
        return floatValue

    def modifyUpperCase(self, valueA: str):
        return valueA.upper()

    def modifyLowerCase(self, valueA: str):
        return valueA.lower()

    def parseModify(self, resultsToModify: (set, set), modifyQueries: list) -> (set, set):
        """
        modifyQueries:
        [[("MODIFY" | "RMODIFY"), <User Input>, ("NUMIFY" | "UPPERCASE" | "LOWERCASE")], ...]
        """

        matchingFields = resultsToModify[1]

        modifiedUIDs = set()
        numifiedFields = set()

        for modification in modifyQueries:
            userInput1 = modification[1]
            modificationType = modification[2]
            modifyFields = []
            if modification[0] == "MODIFY":
                if userInput1 in resultsToModify[1]:
                    modifyFields.append(userInput1)
            else:
                try:
                    userInputRegex = re.compile(userInput1)
                    modifyFields = [fieldMatch for fieldMatch in matchingFields if userInputRegex.match(fieldMatch)]
                except (ValueError, re.error):
                    continue
            for entity in self.allEntities:
                for modifyField in modifyFields:
                    entityFieldValue = self.allEntities[entity].get(modifyField)
                    if entityFieldValue is None or modificationType not in ["UPPERCASE", "LOWERCASE", "NUMIFY"]:
                        newFieldValue = None
                    elif modificationType == "UPPERCASE":
                        newFieldValue = self.modifyUpperCase(entityFieldValue)
                    elif modificationType == "LOWERCASE":
                        newFieldValue = self.modifyLowerCase(entityFieldValue)
                    else:
                        newFieldValue = str(self.modifyNumify(entityFieldValue))
                        numifiedFields.add(modifyField)
                    if newFieldValue is not None:
                        modifiedUIDs.add(entity)
                        self.allEntities[entity][modifyField] = newFieldValue

        return modifiedUIDs, numifiedFields

    def parseQuery(self, mainWindow, selectClause: str, selectValue: Union[str, list], sourceClause: str,
                   sourceValues: Union[None, list], conditionClauses: Union[None, list],
                   modifyQueries: Union[list, None] = None) -> Optional[
        tuple[Optional[tuple[set, Union[set[Any], set[Union[str, Any]]]]],
        Optional[tuple[set[Any], set[Any]]]]]:

        if self.databaseSnapshot is None:
            return None
        self.allEntities = dict(self.allEntitiesInit)

        returnValue = None
        modifications = None
        if fieldsToSelect := self.parseSelect(selectClause, selectValue):
            if entitiesToConsider := self.parseSource(sourceClause, sourceValues, fieldsToSelect):
                if conditionClauses:
                    entitiesToConsider = self.parseConditions(mainWindow, conditionClauses, entitiesToConsider)
                returnValue = (entitiesToConsider, fieldsToSelect)
                if modifyQueries:
                    modifications = self.parseModify(returnValue, modifyQueries)

        queryUID = str(uuid4())
        self.QUERIES_HISTORY[queryUID] = (selectClause, selectValue, sourceClause, sourceValues, conditionClauses,
                                          modifyQueries)

        return returnValue, modifications
