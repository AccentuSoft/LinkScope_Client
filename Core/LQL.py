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

    def parseSelect(self, selectClause: str, selectValue: Union[str, list], entityFieldsList: list):
        if selectClause == 'SELECT':
            if '*' in selectValue:
                return entityFieldsList
            return [entityField for entityField in selectValue if entityField in entityFieldsList]
        else:
            clauseValue = re.compile(selectValue)
            return [entityField for entityField in entityFieldsList if clauseValue.match(entityField)]

    def parseSource(self, sourceClause: str, sourceValues: Union[None, list], canvasesList: list):
        if sourceClause == "FROMDB":
            return True
        else:
            resultEntitySet = set()
            for sourceValue in sourceValues:
                if sourceValue[1] == "CANVAS":
                    if sourceValue not in canvasesList:
                        return
                    matchingCanvases = [sourceValue]
                else:
                    canvasRegex = re.compile(sourceValue[3])
                    matchingCanvases = [canvasMatch for canvasMatch in canvasesList if canvasRegex.match(canvasMatch)]
                for matchingCanvas in matchingCanvases:
                    if sourceValue[0] == 'AND':
                        if sourceValue[2] is False:
                            resultEntitySet = self.canvasAndNot(resultEntitySet, )  # TODO - move all of this into LQLQuerybuilder
                    else:
                        pass
                    if sourceValue[1] is None:
                        pass
                    else:
                        pass

            return [canvas for canvas in sourceValues if canvas in canvasesList]

    def canvasOr(self, canvasSetA: set, canvasSetB: set):
        return canvasSetA.union(canvasSetB)

    def canvasAnd(self, canvasSetA: set, canvasSetB: set):
        return canvasSetA.intersection(canvasSetB)

    def canvasAndNot(self, canvasSetA: set, canvasSetB: set):
        return canvasSetA.difference(canvasSetB)

    def canvasOrNot(self, canvasSetA: set, canvasSetB: set, allEntitiesSet: set):
        return canvasSetA.union(allEntitiesSet.difference(canvasSetB))

    def parseQuery(self, selectClause: str, selectValue: Union[str, list], sourceClause: str,
                   sourceValues: Union[None, list]):
        pass

    def parseModify(self):
        pass


class LQLQueryBuilder:

    QUERY_PARTS_DICT = {"query": Query,
                        "select-query": SelectQuery}

    QUERIES_HISTORY = []

    def __init__(self, mainWindow):
        self.mainWindow = mainWindow

    def getAllEntityFields(self) -> set:
        entitiesSnapshot = self.mainWindow.LENTDB.getAllEntities()
        entityFields = set()
        for entity in entitiesSnapshot:
            entityFields.update(entity.keys())
        entityFields.update('*')
        return entityFields

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
