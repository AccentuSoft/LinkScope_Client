#!/usr/bin/env python3

import contextlib
import importlib.util
import sys
from os import listdir
from pathlib import Path
from uuid import uuid4
from typing import Union
from shutil import move
from msgpack import dump, load


class ResolutionManager:

    # Load all resources needed.
    def __init__(self, mainWindow, messageHandler):
        self.messageHandler = messageHandler
        self.mainWindow = mainWindow
        self.resolutions = {}
        # Macro dict item contents: tuple of (resolution, parameter values)
        self.macros = {}

    def loadResolutionsFromDir(self, directory: Path) -> None:
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
                    self.messageHandler.info(f"Loaded Resolution: {resNameString}")
            except Exception as e:
                self.messageHandler.error(f"Cannot load resolutions from {str(directory)}" + "\n Info: " + repr(e))
                exceptionsCount += 1
                if exceptionsCount > 3:
                    # Will not occur when loading modules with 3 or fewer resolutions, but that should be fine.
                    self.messageHandler.critical("Failed loading too many resolutions to proceed.")
                    sys.exit(5)

    def getResolutionParameters(self, resolutionCategory, resolutionNameString):
        resolutionsList = self.resolutions.get(resolutionCategory)
        if resolutionsList is not None and resolutionNameString in resolutionsList:
            return self.resolutions[resolutionCategory][resolutionNameString]['parameters']
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
                    self.mainWindow.executeRemoteResolution(resolutionCategoryNameString, resolutionEntitiesInput,
                                                            parameters, resolutionUID)
                    # Returning a bool, so we know that the resolution is running on the server.
                    return True
                resolutionClass = self.resolutions[resolutionCategory][resolutionName]['resolution']()
                return resolutionClass.resolution(resolutionEntitiesInput, parameters)
        return None

    def createMacro(self, resolutionList: list) -> str:
        macroUID = str(uuid4())
        self.macros[macroUID] = resolutionList

        return macroUID

    def deleteMacro(self, macroUID: str) -> bool:
        # We don't have to worry about running macros, because the details of the macro are saved in memory.
        # We do however want to get the thread lock because of potential race conditions.
        try:
            with self.mainWindow.macrosLock:
                self.macros.pop(macroUID)
            return True
        except KeyError:
            return False

    def getMacroFilePath(self):
        return Path(self.mainWindow.SETTINGS.value("Program/BaseDir")) / "Macros.lsmacros"

    def loadMacros(self):
        # Load AFTER we load resolutions.
        macroFilePath = self.getMacroFilePath()

        try:
            with open(macroFilePath, "rb") as macroFile:
                self.macros = load(macroFile)
        except ValueError:
            # If the Macros file is empty or contains invalid input, ignore it.
            pass
        except FileNotFoundError:
            # Create new placeholder notes file if it doesn't exist.
            try:
                macroFilePath.touch(0o700, exist_ok=False)
                self.mainWindow.MESSAGEHANDLER.info('Created new Macros file.')
            except FileExistsError:
                self.mainWindow.MESSAGEHANDLER.error('Race condition occurred while trying to create Macros file.')

    def save(self):
        macroFilePath = self.getMacroFilePath()
        macroFilePathTmp = macroFilePath.with_suffix(f'{macroFilePath.suffix}.tmp')

        with open(macroFilePathTmp, "wb") as macroFile:
            dump(self.macros, macroFile)
        move(macroFilePathTmp, macroFilePath)
