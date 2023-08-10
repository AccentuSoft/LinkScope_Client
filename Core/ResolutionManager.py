#!/usr/bin/env python3

import contextlib
import importlib.util
import sys
from os import listdir
from pathlib import Path
from uuid import uuid4
from typing import Union, Any

from PySide6 import QtCore, QtWidgets, QtGui
from Core.ResourceHandler import StringPropertyInput, FilePropertyInput, SingleChoicePropertyInput, \
    MultiChoicePropertyInput


class ResolutionManager:

    # Load all resources needed.
    def __init__(self, mainWindow):
        self.mainWindow = mainWindow
        self.resolutions = {}
        # Macro dict item contents: tuple of (resolution, parameter values)
        self.macros = {}

        self.loadResolutionsFromDir(
            Path(self.mainWindow.SETTINGS.value("Program/BaseDir")) / "Core" / "Resolutions" / "Core")

    def loadResolutionsFromDir(self, directory: Path) -> list:
        resolutionsLoaded = []
        exceptionsCount = 0
        for resolution in listdir(directory):
            resolution = str(resolution)
            try:
                if resolution.endswith('.py'):
                    resolutionName = resolution[:-3]
                    spec = importlib.util.spec_from_file_location(
                        resolutionName,
                        directory / resolution)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    resClass = getattr(module, resolutionName)
                    resClassInst = resClass()
                    resNameString = resClassInst.name.replace('_', ' ')
                    resolutionDesc = resClassInst.description
                    originTypes = resClassInst.originTypes
                    resultTypes = resClassInst.resultTypes
                    resolutionParameters = resClassInst.parameters
                    with contextlib.suppress(AttributeError):
                        resolutionCategory = resClassInst.category
                        if not isinstance(resolutionCategory, str):
                            resolutionCategory = "Uncategorized"
                    if self.resolutions.get(resolutionCategory) is None:
                        self.resolutions[resolutionCategory] = {}
                    self.resolutions[resolutionCategory][resNameString] = {'name': resNameString,
                                                                           'description': resolutionDesc,
                                                                           'originTypes': originTypes,
                                                                           'resultTypes': resultTypes,
                                                                           'parameters': resolutionParameters,
                                                                           'category': resolutionCategory,
                                                                           'resolution': resClass
                                                                           }
                    self.mainWindow.MESSAGEHANDLER.debug(f"Loaded Resolution: {resNameString}")
                    resolutionsLoaded.append(f'{resolutionCategory}/{resNameString}')
            except Exception as e:
                self.mainWindow.MESSAGEHANDLER.error(
                    f"Cannot load resolutions from {str(directory)}\n Info: {repr(e)}")
                exceptionsCount += 1
                if exceptionsCount > 3:
                    # Will not occur when loading modules with 3 or fewer resolutions, but that should be fine.
                    self.mainWindow.MESSAGEHANDLER.critical("Failed loading too many resolutions to proceed.")
                    sys.exit(5)
        return resolutionsLoaded

    def getResolutionParameters(self, resolutionCategory, resolutionNameString):
        resolutionsList = self.resolutions.get(resolutionCategory)
        if resolutionsList is not None and resolutionNameString in resolutionsList:
            return dict(self.resolutions[resolutionCategory][resolutionNameString]['parameters'])
        return None

    def getResolutionOriginTypes(self, resolutionCategoryNameString: str) -> Union[list, None]:
        resolutionCategory, resolutionName = resolutionCategoryNameString.split('/', 1)
        with contextlib.suppress(TypeError):
            if resolutionName in self.resolutions.get(resolutionCategory):
                originTypes = self.resolutions[resolutionCategory][resolutionName]['originTypes']
                if '*' in originTypes:
                    originTypes = self.mainWindow.RESOURCEHANDLER.getAllEntities()
                return originTypes
        return None

    def getResolutionDescription(self, resolutionCategoryNameString: str) -> Union[str, None]:
        resolutionCategory, resolutionName = resolutionCategoryNameString.split('/', 1)
        with contextlib.suppress(TypeError):
            if resolutionName in self.resolutions.get(resolutionCategory):
                return self.resolutions[resolutionCategory][resolutionName].get('description', '')
        return None

    def loadResolutionsFromServer(self, serverRes) -> None:
        for category in serverRes:
            if category not in self.resolutions:
                self.resolutions[category] = {}
            for serverResolution in serverRes[category]:
                self.resolutions[category][serverResolution] = serverRes[category][serverResolution]

    def removeServerResolutions(self) -> None:
        for category in dict(self.resolutions):
            for resolution in dict(self.resolutions[category]):
                # If resolution class does not exist locally, then assume it exists on the server.
                if self.resolutions[category][resolution]['resolution'] == '':
                    self.resolutions[category].pop(resolution)
        for category in dict(self.resolutions):
            if len(self.resolutions[category]) == 0:
                self.resolutions.pop(category)

    def getResolutionCategories(self) -> list:
        return list(self.resolutions)

    def getResolutionsForEntityTypesByCategory(self, eTypes) -> dict:
        """
        Gets a set of entity types, and returns a dictionary with all the resolutions that can take all
        included types as input.
        If '*' is part of eTypes, get all Resolutions of all categories.
        """
        result = {}
        for category in self.resolutions:
            result[category] = []
            for resolution in self.resolutions[category]:
                originTypes = self.resolutions[category][resolution]['originTypes']
                if eTypes.issubset(originTypes) or '*' in originTypes:
                    result[category].append(resolution)
        return result

    def getResolutionsInCategory(self, category) -> list:
        return list(self.resolutions[category]) if category in self.resolutions else []

    def getAllResolutions(self) -> list:
        categories = self.getResolutionCategories()
        result = []
        for category in categories:
            result += self.getResolutionsInCategory(category)
        return result

    def executeResolution(self, resolutionCategoryNameString: str, resolutionEntitiesInput: list, parameters: dict,
                          resolutionUID: str):
        resolutionCategory, resolutionName = resolutionCategoryNameString.split('/', 1)
        with contextlib.suppress(TypeError):
            if resolutionName in self.resolutions.get(resolutionCategory):
                if self.resolutions[resolutionCategory][resolutionName].get('resolution') == '':
                    # If resolution class does not exist locally, then assume it exists on the server.
                    self.mainWindow.FCOM.runRemoteResolution(
                        resolutionCategoryNameString, resolutionEntitiesInput, parameters, resolutionUID)
                    # Returning a bool, so we know that the resolution is running on the server.
                    return True
                resolutionClass = self.resolutions[resolutionCategory][resolutionName]['resolution']()
                return resolutionClass.resolution(resolutionEntitiesInput, parameters)
        return None

    def createMacro(self, resolutionList: list) -> str:
        macroUID = str(uuid4())
        self.macros[macroUID] = resolutionList

        return macroUID

    def renameMacro(self, oldName: str, newName: str) -> bool:
        if oldName != newName:
            with self.mainWindow.macrosLock:
                if newName in self.macros:
                    self.mainWindow.MESSAGEHANDLER.warning('The specified name already exists. '
                                                           'Macro names must be unique.',
                                                           popUp=True)
                    return False
                if oldName not in self.macros:
                    self.mainWindow.MESSAGEHANDLER.error('Attempting to rename a nonexistent macro.', popUp=True)
                    return False
                oldMacro = self.macros.pop(oldName)
                self.macros[newName] = oldMacro
        return True

    def deleteMacro(self, macroUID: str) -> bool:
        # We don't have to worry about running macros, because the details of the macro are saved in memory.
        # We do however want to get the thread lock because of potential race conditions.
        try:
            with self.mainWindow.macrosLock:
                self.macros.pop(macroUID)
            return True
        except KeyError:
            return False

    def loadMacros(self) -> None:
        # Load AFTER we load resolutions.
        self.macros = self.mainWindow.SETTINGS.value("Program/Macros", {})

    def save(self) -> None:
        self.mainWindow.SETTINGS.setGlobalValue("Program/Macros", self.macros)


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


class ResolutionSearchResultsList(QtWidgets.QListWidget):

    def __init__(self, mainWindowObject):
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

    def __init__(self, parent, entityList: list, resolutionDict: dict):
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


class ResolutionExecutorThread(QtCore.QThread):
    sig = QtCore.Signal(str, list, str)
    sigStr = QtCore.Signal(str, str, str)
    sigError = QtCore.Signal(str)

    def __init__(self, resolution: str, resolutionArgument: list, resolutionParameters: dict,
                 mainWindowObject, uid: str):
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


class MacroDialog(QtWidgets.QDialog):

    def __init__(self, mainWindowObject):
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

