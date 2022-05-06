#!/usr/bin/env python3

import importlib
import sys
from os import listdir
from pathlib import Path
from typing import Union

from PySide6 import QtWidgets, QtGui
from Core.Interface import Stylesheets


class ResolutionManager:

    # Load all resources needed.
    def __init__(self, mainWindow, messageHandler):
        self.messageHandler = messageHandler
        self.mainWindow = mainWindow
        self.resolutions = {}

    def loadResolutionsFromDir(self, directory: Path):
        exceptionsCount = 0
        for resolution in listdir(directory):
            resolution = str(resolution)
            resolutionCategory = "Uncategorized"
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
                    try:
                        resolutionCategory = resClassInst.category
                        if not isinstance(resolutionCategory, str):
                            raise AttributeError()
                    except AttributeError:
                        pass
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
                    self.messageHandler.info("Loaded Resolution: " + resNameString)
            except Exception as e:
                self.messageHandler.error("Cannot load resolutions from " + str(directory) + "\n Info: " + repr(e))
                exceptionsCount += 1
                if exceptionsCount > 3:
                    # Will not occur when loading modules with 3 or fewer resolutions, but that should be fine.
                    self.messageHandler.critical("Failed loading too many resolutions to proceed.")
                    sys.exit(5)

    def getResolutionParameters(self, resolutionCategory, resolutionNameString):
        resolutionsList = self.resolutions.get(resolutionCategory)
        if resolutionsList is not None and resolutionNameString in resolutionsList:
            parameters = self.resolutions[resolutionCategory][resolutionNameString]['parameters']
            return parameters
        return None

    def getResolutionOriginTypes(self, resolutionNameString: str) -> Union[list, None]:
        for category in self.resolutions:
            if resolutionNameString in self.resolutions[category]:
                originTypes = self.resolutions[category][resolutionNameString]['originTypes']
                if '*' in originTypes:
                    originTypes = self.mainWindow.RESOURCEHANDLER.getAllEntities()
                return originTypes
        return None

    def getResolutionDescription(self, resolutionNameString: str) -> Union[str, None]:
        for category in self.resolutions:
            if resolutionNameString in self.resolutions[category]:
                resolutionDescription = self.resolutions[category][resolutionNameString].get('description', '')
                return resolutionDescription
        return None

    def loadResolutionsFromServer(self, serverRes):
        for category in serverRes:
            if category not in self.resolutions:
                self.resolutions[category] = {}
            for serverResolution in serverRes[category]:
                self.resolutions[category][serverResolution] = serverRes[category][serverResolution]

    def removeServerResolutions(self):
        for category in dict(self.resolutions):
            for resolution in dict(self.resolutions[category]):
                # If resolution class does not exist locally, then assume it exists on the server.
                if self.resolutions[category][resolution]['resolution'] == '':
                    self.resolutions[category].pop(resolution)
        for category in dict(self.resolutions):
            if len(self.resolutions[category]) == 0:
                self.resolutions.pop(category)

    def getResolutionCategories(self):
        result = []
        for category in self.resolutions:
            result.append(category)
        return result

    def getResolutionsForEntityTypesByCategory(self, eTypes):
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

    def getResolutionsInCategory(self, category):
        if category in self.resolutions:
            return list(self.resolutions[category])
        return []

    def getAllResolutions(self):
        categories = self.getResolutionCategories()
        result = []
        for category in categories:
            result += self.getResolutionsInCategory(category)
        return result

    def executeResolution(self, resolutionName: str, resolutionEntitiesInput: list, parameters: dict,
                          resolutionUID: str):
        for category in self.resolutions:
            for resolution in self.resolutions[category]:
                if self.resolutions[category][resolution]['name'] == resolutionName:
                    # If resolution class does not exist locally, then assume it exists on the server.
                    if self.resolutions[category][resolution]['resolution'] == '':
                        self.mainWindow.executeRemoteResolution(resolutionName, resolutionEntitiesInput, parameters,
                                                                resolutionUID)
                        # Returning a bool, so we know that the resolution is running on the server.
                        return True

                    resolutionClass = self.resolutions[category][resolution]['resolution']()
                    result = resolutionClass.resolution(resolutionEntitiesInput, parameters)
                    return result


class StringPropertyInput(QtWidgets.QLineEdit):

    def __init__(self, placeholderText, defaultText):
        super(StringPropertyInput, self).__init__()
        self.setPlaceholderText(placeholderText)
        if defaultText is not None:
            self.setText(defaultText)

    def getValue(self):
        return self.text()


class FilePropertyInput(QtWidgets.QLineEdit):

    def __init__(self, placeholderText, defaultText):
        super(FilePropertyInput, self).__init__()
        self.setPlaceholderText(placeholderText)
        if defaultText is not None:
            self.setText(defaultText)
        self.fileDialog = QtWidgets.QFileDialog()

    def getValue(self):
        return self.text()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        fileChosen = self.fileDialog.getOpenFileName(self,
                                                     "Open File",
                                                     str(Path.home()),
                                                     options=QtWidgets.QFileDialog.DontUseNativeDialog)
        self.setText(fileChosen[0])


class SingleChoicePropertyInput(QtWidgets.QGroupBox):

    def __init__(self, optionsSet: set, defaultOption):
        # Ensure that the options given are an actual set (i.e. each one is unique)
        enforceOptionsSet = set(optionsSet)
        super(SingleChoicePropertyInput, self).__init__(title='Option Selection')
        vboxLayout = QtWidgets.QVBoxLayout()
        self.setLayout(vboxLayout)

        self.options = []
        if defaultOption is None:
            defaultOption = ''

        for option in enforceOptionsSet:
            radioButton = QtWidgets.QRadioButton(option)
            radioButton.setStyleSheet(Stylesheets.RADIO_BUTTON_STYLESHEET)
            if option == defaultOption:
                radioButton.setChecked(True)
            else:
                radioButton.setChecked(False)
            self.options.append(radioButton)
            vboxLayout.addWidget(radioButton)

    def getValue(self):
        for option in self.options:
            if option.isChecked():
                return option.text()

        return ''


class MultiChoicePropertyInput(QtWidgets.QGroupBox):

    def __init__(self, optionsSet: set, defaultOptions):
        # Ensure that the options given are an actual set (i.e. each one is unique)
        enforceOptionsSet = set(optionsSet)
        super(MultiChoicePropertyInput, self).__init__(title='Option Selection')
        vboxLayout = QtWidgets.QVBoxLayout()
        self.setLayout(vboxLayout)

        self.options = []
        if defaultOptions is None:
            defaultOptions = []

        for option in enforceOptionsSet:
            checkBox = QtWidgets.QCheckBox(option)
            checkBox.setStyleSheet(Stylesheets.CHECK_BOX_STYLESHEET)
            if option in defaultOptions:
                checkBox.setChecked(True)
            else:
                checkBox.setChecked(False)
            self.options.append(checkBox)
            vboxLayout.addWidget(checkBox)

    def getValue(self):
        valuesSelected = []
        for option in self.options:
            if option.isChecked():
                valuesSelected.append(option.text())

        return valuesSelected
