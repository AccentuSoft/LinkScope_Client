#!/usr/bin/env python3

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

    def parseQuery(self, selectText, selectOption):
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

    def getAllCanvasNames(self) -> list:
        canvasNames = list(self.mainWindow.centralWidget().tabbedPane.canvasTabs.keys())
        canvasNames.append('*')
        return canvasNames
