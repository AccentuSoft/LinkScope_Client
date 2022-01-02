#!/usr/bin/env python3

import importlib
import sys
from os import listdir
from pathlib import Path


class ResolutionManager:

    # Load all resources needed.
    def __init__(self, mainWindow, messageHandler):
        self.messageHandler = messageHandler
        self.mainWindow = mainWindow
        self.resolutions = {}

    def loadResolutionsFromDir(self, directory: Path):
        exceptionsCount = 0
        if self.resolutions.get(directory.stem) is None:
            self.resolutions[directory.stem] = {}
        for resolution in listdir(directory):
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
                    self.resolutions[directory.stem][resNameString] = {'name': resNameString,
                                                                       'description': resolutionDesc,
                                                                       'originTypes': originTypes,
                                                                       'resultTypes': resultTypes,
                                                                       'parameters': resolutionParameters,
                                                                       'resolution': resClass
                                                                       }
                    self.messageHandler.info("Loaded Resolution: " + resNameString)
            except Exception as e:
                self.messageHandler.error("Cannot load resolutions from " + str(directory) + "\n Info: " + repr(e))
                exceptionsCount += 1
                if exceptionsCount > 5:
                    self.messageHandler.critical("Failed loading too many modules to proceed.")
                    sys.exit(5)

    def getResolutionParameters(self, resolutionCategory, resolutionNameString):
        resolutionsList = self.resolutions.get(resolutionCategory)
        if resolutionsList is not None and resolutionNameString in resolutionsList:
            parameters = self.resolutions[resolutionCategory][resolutionNameString]['parameters']
            return parameters
        return None

    def getResolutionOriginTypes(self, resolutionNameString):
        for category in self.resolutions:
            if resolutionNameString in self.resolutions[category]:
                originTypes = self.resolutions[category][resolutionNameString]['originTypes']
                if '*' in originTypes:
                    originTypes = self.mainWindow.RESOURCEHANDLER.getAllEntities()
                return originTypes
        return None

    def loadResolutionsFromServer(self, serverRes):
        self.resolutions |= serverRes

    def removeServerResolutions(self):
        try:
            self.resolutions.pop("Server Resolutions")
        except KeyError:
            pass

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
                    if category == "Server Resolutions":
                        self.mainWindow.executeRemoteResolution(resolutionName, resolutionEntitiesInput, parameters,
                                                                resolutionUID)
                        # Returning a bool so we know that the resolution is running on the server.
                        return True

                    resolutionClass = self.resolutions[category][resolution]['resolution']()
                    result = resolutionClass.resolution(resolutionEntitiesInput, parameters)
                    return result
