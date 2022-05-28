#!/usr/bin/env python3

from typing import Union
import re

"""
This class handles the backend stuff for the LinkScope Query Language.
"""


class Query:
    COMPONENTS = ["select-query"]

    def __init__(self):
        super(Query, self).__init__()


class SelectQuery:

    def __init__(self):
        super(SelectQuery, self).__init__()


class LQLQueryParser:
    pass


class LQLQueryBuilder:
    QUERY_PARTS_DICT = {"query": Query,
                        "select-query": SelectQuery}

    QUERIES_HISTORY = {}

    def __init__(self, mainWindow):
        self.mainWindow = mainWindow
        self.allCanvases = self.getAllCanvasNames()
        self.allEntityFields, self.allEntities = self.getAllEntitiesAndFields()
        self.databaseEntities = self.getAllUIDs()
        self.canvasesEntitiesDict = self.getCanvasesEntitiesDict(self.allCanvases)

    def getAllEntitiesAndFields(self) -> (set, list):
        entitiesSnapshot = {entity['uid']: entity for entity in self.mainWindow.LENTDB.getAllEntities()
                            if entity.get('Entity Type') != 'EntityGroup'}
        entityFields = set()
        for entityUID in entitiesSnapshot:
            entityFields.update(entitiesSnapshot[entityUID].keys())
        entityFields.update('*')
        entityFields.remove('Entity Type')
        entityFields.remove('uid')
        return entityFields, entitiesSnapshot

    def getAllUIDs(self) -> set:
        return self.mainWindow.LENTDB.getAllEntityUIDs()

    def getAllCanvasNames(self) -> list:
        canvasNames = list(self.mainWindow.centralWidget().tabbedPane.canvasTabs.keys())
        canvasNames.append('*')
        return canvasNames

    def getEntitiesOnCanvas(self, canvasName: str):
        try:
            return set(self.mainWindow.centralWidget().tabbedPane.canvasTabs[canvasName].sceneGraph.nodes)
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
            if '*' in selectValue:
                # No need to remove the '*'. Could cause errors if that's a field name (even though it is bad practice).
                return self.allEntityFields
            return [entityField for entityField in selectValue if entityField in self.allEntityFields]
        else:
            try:
                clauseValue = re.compile(selectValue)
                return [entityField for entityField in self.allEntityFields if clauseValue.match(entityField)]
            except re.error:
                return []

    def parseSource(self, sourceClause: str, sourceValues: Union[None, list]):
        """
        sourceValues:
        [[("AND"|"OR"|None), ("CANVAS"|"RCANVAS"), (True|False), <User Input>], ...]
        """
        if sourceClause == "FROMDB":
            return self.databaseEntities
        else:
            resultEntitySet = set()
            for sourceValue in sourceValues:
                try:
                    if sourceValue[1] == "CANVAS":
                        if sourceValue[3] not in self.allCanvases:
                            raise ValueError('Reference to nonexistent canvas.')
                        matchingCanvases = [sourceValue]
                    else:
                        canvasRegex = re.compile(sourceValue[3])
                        matchingCanvases = [canvasMatch for canvasMatch in self.allCanvases
                                            if canvasRegex.match(canvasMatch)]
                except (ValueError, re.error):
                    continue

                # Not the most efficient way of phrasing this, but by far the most compact and legible.
                for matchingCanvas in matchingCanvases:
                    if sourceValue[0] == 'AND':
                        if sourceValue[2] is False:
                            resultEntitySet = self.canvasAndNot(resultEntitySet,
                                                                self.canvasesEntitiesDict[matchingCanvas])
                        else:
                            resultEntitySet = self.canvasAnd(resultEntitySet,
                                                             self.canvasesEntitiesDict[matchingCanvas])
                    else:
                        # If this is the first clause, or'ing the empty initial resultEntitySet is what we want.
                        if sourceValue[2] is False:
                            resultEntitySet = self.canvasOrNot(resultEntitySet,
                                                               self.canvasesEntitiesDict[matchingCanvas],
                                                               self.databaseEntities)
                        else:
                            resultEntitySet = self.canvasOr(resultEntitySet,
                                                            self.canvasesEntitiesDict[matchingCanvas])

            return resultEntitySet

    def parseConditions(self, conditionClauses: Union[None, list], entitiesPool):
        """
        conditionClauses:
        [[("AND", "OR", None), ("VC"|"GC"), (True | False), conditionValue], ...]

        conditionValue:
            if VC:
                [("ATTRIBUTE" | "RATTRIBUTE"), <User Input>,
                ("EQ" | "CONTAINS" | "STARTSWITH" | "ENDSWITH" | "RMATCH"), <User Input>]
            if GC:
                [("CHILDOF" <ENTITY> | "PARENTOF" <ENTITY> |
                "NUMCHILDREN" (" < " | " <= " | " > " | " >= " | " == ") <DIGITS> |
                "NUMPARENTS" (" < " | " <= " | " > " | " >= " | " == ") <DIGITS> |
                "PATHTO" <ENTITY> | "ISOLATED" | "ISROOT" | "ISLEAF")]
        """

        self.allEntities = {uid: self.allEntities[uid] for uid in self.allEntities if uid in entitiesPool}
        uidsToSelect = set()

        for conditionClause in conditionClauses:
            conditionValue = conditionClause[3]
            userInput1 = conditionValue[1]
            userInput2 = conditionValue[3]
            if conditionClause[1] == "VC":
                matchingFields = []
                if conditionValue[0] == "ATTRIBUTE":
                    if userInput1 in self.allEntityFields:
                        matchingFields.append(userInput1)
                else:
                    try:
                        attributeRegex = re.compile(userInput1)
                    except re.error:
                        continue
                    for field in self.allEntityFields:
                        if attributeRegex.match(field):
                            matchingFields.append(field)

                for matchingField in matchingFields:
                    entitiesToRemove = []
                    for entity in self.allEntities:
                        attributeKeyValue = str(self.allEntities[entity].get(matchingField))
                        if not self.checkVCHelper(conditionValue[2], conditionClause[2], attributeKeyValue,
                                                  userInput2):
                            if conditionClause[0] == "AND":
                                entitiesToRemove.append(entity)
                        else:
                            uidsToSelect.add(entity)
                    for entityToRemove in entitiesToRemove:
                        uidsToSelect.remove(entityToRemove)

            elif conditionClause[1] == "GC":
                pass

    def canvasOr(self, canvasSetA: set, canvasSetB: set):
        return canvasSetA.union(canvasSetB)

    def canvasAnd(self, canvasSetA: set, canvasSetB: set):
        return canvasSetA.intersection(canvasSetB)

    def canvasAndNot(self, canvasSetA: set, canvasSetB: set):
        return canvasSetA.difference(canvasSetB)

    def canvasOrNot(self, canvasSetA: set, canvasSetB: set, allEntitiesSet: set):
        return canvasSetA.union(allEntitiesSet.difference(canvasSetB))

    def checkEQ(self, valueA: str, valueB: str):
        if valueA == valueB:
            return True
        return False

    def checkContains(self, valueA: str, valueB: str):
        if valueB in valueA:
            return True
        return False

    def checkStartsWith(self, valueA: str, valueB: str):
        if valueA.startswith(valueB):
            return True
        return False

    def checkEndsWith(self, valueA: str, valueB: str):
        if valueA.endswith(valueB):
            return True
        return False

    def checkRMatch(self, valueA: str, valueB: str):
        try:
            valueMatch = re.compile(valueB)
            if valueMatch.match(valueA):
                return True
        except re.error:
            pass
        return False

    def checkVCHelper(self, checkType: str, isNot: bool, valueA: str, valueB: str):
        returnVal = False
        if checkType == "EQ":
            returnVal = self.checkEQ(valueA, valueB)
        elif checkType == "CONTAINS":
            returnVal = self.checkContains(valueA, valueB)
        elif checkType == "STARTSWITH":
            returnVal = self.checkStartsWith(valueA, valueB)
        elif checkType == "ENDSWITH":
            returnVal = self.checkEndsWith(valueA, valueB)
        elif checkType == "RMATCH":
            returnVal = self.checkRMatch(valueA, valueB)
        if isNot:
            return not returnVal
        return returnVal

    def checkChildOf(self, valueA: str, valueB: str):
        return False

    def checkSuccessorOf(self, valueA: str, valueB: str):
        return False

    def checkParentOf(self, valueA: str, valueB: str):
        return False

    def checkPredecessorOf(self, valueA: str, valueB: str):
        return False

    def checkGCHelper(self, checkType: str, isNot: bool, args: list):
        returnVal = False
        if checkType == "CHILDOF":
            returnVal = self.checkChildOf(*args)
        if isNot:
            return not returnVal
        return returnVal

    def parseQuery(self, selectClause: str, selectValue: Union[str, list], sourceClause: str,
                   sourceValues: Union[None, list], conditionClauses: Union[None, list]):
        pass

    def parseModify(self):
        pass
