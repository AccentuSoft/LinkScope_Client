#!/usr/bin/env python3

import contextlib
from typing import Union, Optional, Any
from uuid import uuid4
import re
import networkx as nx
import string

from Core.GlobalVariables import non_string_fields

"""
This class handles the backend stuff for the LinkScope Query Language.
"""


class LQLQueryBuilder:
    QUERIES_HISTORY = {}

    databaseSnapshot = None
    databaseEntities = None
    allCanvases = None
    canvasesEntitiesDict = None
    allEntityFields = None
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
        self.allEntityFields, self.allEntities = self.getAllEntitiesAndFields()

        # Re-define database entities to remove Group Entities
        self.databaseEntities = set(self.allEntities.keys())

    def getAllEntitiesAndFields(self) -> (set, list):
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
                        resultEntitySet = self.canvasAndNot(resultEntitySet, self.canvasesEntitiesDict[matchingCanvas])\
                            if sourceValue[2] is True else\
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

    def parseConditions(self, conditionClauses: Union[None, list], entitiesPool) -> set:
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
                "CONNECTEDTO" <ENTITY> | "ISOLATED" | "ISROOT" | "ISLEAF")]
        """

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

    def checkNumChildren(self, valueA: str, valueB: str, valueC: int):
        numChildren = len(list(self.databaseSnapshot.successors(valueA)))
        return (valueB == "<" and numChildren < valueC) or \
               (valueB == "<=" and numChildren <= valueC) or \
               (valueB == ">" and numChildren > valueC) or \
               (valueB == ">=" and numChildren >= valueC) or \
               (valueB == "==" and numChildren == valueC)

    def checkNumParents(self, valueA: str, valueB: str, valueC: int):
        numParents = len(list(self.databaseSnapshot.predecessors(valueA)))
        return (valueB == "<" and numParents < valueC) or \
               (valueB == "<=" and numParents <= valueC) or \
               (valueB == ">" and numParents > valueC) or \
               (valueB == ">=" and numParents >= valueC) or \
               (valueB == "==" and numParents == valueC)

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
        elif checkType == "PARENTOF":
            returnVal = self.checkParentOf(*args)
        return not returnVal if isNot else returnVal

    def modifyNumify(self, valueA: str):
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
        return str(floatValue)

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
                        newFieldValue = self.modifyNumify(entityFieldValue)
                        numifiedFields.add(modifyField)
                    if newFieldValue is not None:
                        modifiedUIDs.add(entity)
                        self.allEntities[entity][modifyField] = newFieldValue

        return modifiedUIDs, numifiedFields

    def parseQuery(self, selectClause: str, selectValue: Union[str, list], sourceClause: str,
                   sourceValues: Union[None, list], conditionClauses: Union[None, list],
                   modifyQueries: Union[list, None] = None) -> Optional[tuple[Optional[tuple[set, Union[set[Any], set[Union[str, Any]]]]],
                                                                              Optional[tuple[set[Any], set[Any]]]]]:

        if self.databaseSnapshot is None:
            return None

        returnValue = None
        modifications = None
        if fieldsToSelect := self.parseSelect(selectClause, selectValue):
            if entitiesToConsider := self.parseSource(sourceClause, sourceValues, fieldsToSelect):
                if conditionClauses:
                    entitiesToConsider = self.parseConditions(conditionClauses, entitiesToConsider)
                returnValue = (entitiesToConsider, fieldsToSelect)
                if modifyQueries:
                    modifications = self.parseModify(returnValue, modifyQueries)

        queryUID = str(uuid4())
        self.QUERIES_HISTORY[queryUID] = (selectClause, selectValue, sourceClause, sourceValues, conditionClauses,
                                          modifyQueries)

        return returnValue, modifications
