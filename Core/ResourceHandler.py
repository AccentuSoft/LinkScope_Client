#!/usr/bin/env python3


from typing import Union

import networkx as nx
import re
from defusedxml.ElementTree import parse
from datetime import datetime
from os import listdir
from pathlib import Path
from uuid import uuid4
from ast import literal_eval
from base64 import b64decode
from dateutil import parser

from PySide6.QtGui import QIcon
from PySide6.QtCore import QByteArray


class ResourceHandler:

    def getIcon(self, iconName: str):
        return self.icons[iconName]

    # Load all resources needed.
    def __init__(self, mainWindow, messageHandler) -> None:
        self.mainWindow = mainWindow
        self.messageHandler = messageHandler
        self.entityCategoryList = {}

        self.icons = {"uploading": str(Path(self.mainWindow.SETTINGS.value("Program/BaseDir")) /
                                       "Resources" / "Icons" / "Uploading.png"),
                      "uploaded": str(Path(self.mainWindow.SETTINGS.value("Program/BaseDir")) /
                                      "Resources" / "Icons" / "Uploaded.png"),
                      "upArrow": str(Path(self.mainWindow.SETTINGS.value("Program/BaseDir")) /
                                     "Resources" / "Icons" / "UpArrow.png"),
                      "downArrow": str(Path(self.mainWindow.SETTINGS.value("Program/BaseDir")) /
                                       "Resources" / "Icons" / "DownArrow.png"),
                      "isolatedNodes": str(Path(self.mainWindow.SETTINGS.value("Program/BaseDir")) /
                                           "Resources" / "Icons" / "SelectIsolated.png"),
                      "addCanvas": str(Path(self.mainWindow.SETTINGS.value("Program/BaseDir")) /
                                       "Resources" / "Icons" / "Add_Canvas.png"),
                      "generateReport": str(Path(self.mainWindow.SETTINGS.value("Program/BaseDir")) /
                                            "Resources" / "Icons" / "Generate_Report.png"),
                      "leafNodes": str(Path(self.mainWindow.SETTINGS.value("Program/BaseDir")) /
                                       "Resources" / "Icons" / "SelectLeaf.png"),
                      "nonIsolatedNodes": str(Path(self.mainWindow.SETTINGS.value("Program/BaseDir")) /
                                              "Resources" / "Icons" / "SelectNonIsolated.png"),
                      "rootNodes": str(Path(self.mainWindow.SETTINGS.value("Program/BaseDir")) /
                                       "Resources" / "Icons" / "SelectRoot.png"),
                      "split": str(Path(self.mainWindow.SETTINGS.value("Program/BaseDir")) /
                                   "Resources" / "Icons" / "Split.png"),
                      "merge": str(Path(self.mainWindow.SETTINGS.value("Program/BaseDir")) /
                                   "Resources" / "Icons" / "Merge.png"),
                      "shortestPath": str(Path(self.mainWindow.SETTINGS.value("Program/BaseDir")) /
                                          "Resources" / "Icons" / "ShortestPath.png"),
                      "drawLink": str(Path(self.mainWindow.SETTINGS.value("Program/BaseDir")) /
                                      "Resources" / "Icons" / "DrawLink.png"),
                      "rearrange": str(Path(self.mainWindow.SETTINGS.value("Program/BaseDir")) /
                                       "Resources" / "Icons" / "RearrangeGraph.png"),
                      "colorPicker": str(Path(self.mainWindow.SETTINGS.value("Program/BaseDir")) /
                                         "Resources" / "Icons" / "ColorPicker.png"),
                      }
        # These are not meant to be strict - just restrictive enough such that users don't put in utter nonsense.
        # Note that regex isn't always the best way of validating fields, but it should be good enough for our
        #   purposes.
        self.checks = {'Email': re.compile(r"""(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])"""),
                       'Phonenumber': re.compile(r"""^(\+|00)?[0-9\(\) \-]{3,32}$"""),
                       'String': re.compile(r""".+"""),
                       'URL': re.compile(r"""^https?://(\S(?<!\.)){1,63}(\.(\S(?<!\.)){1,63})+$"""),
                       'Domain': re.compile(r"""^(\S(?<!\.)(?!/)(?<!/)){1,63}(\.(\S(?<!\.)(?!/)(?<!/)){1,63})+$"""),
                       'Float': re.compile(r"""^([-+])?(\d|\.(?=\d))+$"""),
                       'WordString': re.compile(r"""^\D+$"""),
                       'Numbers': re.compile(r"""^\d+$"""),
                       'IPv4': re.compile(r"""^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)(\.(?!$)|$)){4}$"""),
                       'IPv6': re.compile(r"""^(([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]+|::(ffff(:0{1,4})?:)?((25[0-5]|(2[0-4]|1?[0-9])?[0-9])\.){3}(25[0-5]|(2[0-4]|1?[0-9])?[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1?[0-9])?[0-9])\.){3}(25[0-5]|(2[0-4]|1?[0-9])?[0-9]))$"""),
                       'MAC': re.compile(r"""^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"""),
                       'ASN': re.compile(r"""^(AS)?\d+$"""),
                       'CUSIP': re.compile(r"""^[a-zA-Z0-9]{9}$"""),
                       'EIN': re.compile(r"""^\d{2}-?\d{7}$"""),
                       'LEIID': re.compile(r"""^[a-zA-Z0-9]{20}$"""),
                       'ISINID': re.compile(r"""^[a-zA-Z0-9]{2}-?[a-zA-Z0-9]{9}-?[a-zA-Z0-9]$"""),
                       'SIC/NAICS': re.compile(r"""^[0-9]{4,6}$""")}

        self.loadCoreEntities()

    def getEntityCategories(self) -> list:
        eList = []
        for category in self.entityCategoryList:
            eList.append(category)
        return eList

    def getAllEntityDetailsWithIconsInCategory(self, category) -> list:
        eList = []
        for entity in self.entityCategoryList[category]:
            entityValue = self.entityCategoryList[category][entity]
            eList.append((self.getBareBonesEntityJson(entity),
                          entityValue['Icon']
                          ))
        return eList

    def getEntityAttributes(self, entityType) -> Union[None, list]:
        aList = []
        try:
            for category in self.entityCategoryList:
                if entityType in self.entityCategoryList[category]:
                    for attribute in self.entityCategoryList[category][entityType]['Attributes']:
                        aList.append(attribute)
                    break
        except KeyError:
            self.messageHandler.error("Attempted to get attributes for "
                                      "nonexistent entity type: " + str(entityType), True)
            return None
        return aList

    def getAllEntitiesInCategory(self, category) -> list:
        """
        Get all Entity Types in the specified category.
        """
        eList = []
        for entity in self.entityCategoryList[category]:
            eList.append(entity)
        return eList

    def getCategoryOfEntityType(self, entityType: Union[str, None]):
        for category in self.entityCategoryList:
            if entityType in self.entityCategoryList[category]:
                return category
        return None

    def getAllEntities(self) -> list:
        """
        Get all recognised Entity Types.
        """
        eList = []
        for category in self.getEntityCategories():
            for entity in self.getAllEntitiesInCategory(category):
                eList.append(entity)
        return eList

    def validateAttributesOfEntity(self, entityJSON: dict) -> (bool, str):
        try:
            entityType = entityJSON['Entity Type']
            entityCategory = self.getCategoryOfEntityType(entityType)
            # Attributes that become part of the entity after merging are not checked.
            # This is fine, because resolutions (by default) don't assume that any extra fields will be present.
            entityBaseAttributes = self.getEntityAttributes(entityType)
            if entityCategory is not None:
                for attribute in self.entityCategoryList[entityCategory][entityType]['Attributes']:
                    if attribute in entityBaseAttributes:
                        attrValue = entityJSON.get(attribute)
                        if attrValue is None or not self.runCheckOnAttribute(
                                attrValue,
                                self.entityCategoryList[entityCategory][entityType]['Attributes'][attribute][1]):
                            return 'Bad value: ' + str(attrValue)
        except Exception:
            return False
        return True

    def runCheckOnAttribute(self, attribute: str, check: str) -> bool:
        """
        Check that the attribute value given matches the regex of the category 'check'.
        """
        attrCheck = self.checks.get(check)
        if attrCheck is None:
            return False
        result = attrCheck.findall(attribute)
        if len(result) == 1:
            return True
        return False

    def addRecognisedEntityTypes(self, entityFile: Path) -> bool:
        try:
            tree = parse(entityFile, forbid_dtd=True, forbid_entities=True, forbid_external=True)
        except Exception as exc:
            self.mainWindow.MESSAGEHANDLER.warning('Error occurred when loading entities from '
                                                   + str(entityFile) + ': ' + str(exc) + ', skipping.')
            return False

        root = tree.getroot()

        category = root.tag.replace('_', ' ')
        for entity in list(root):
            try:
                entityName = entity.tag.replace('_', ' ')
                attributes = entity.find('Attributes')
                attributesDict = {}
                primaryCount = 0
                for attribute in list(attributes):
                    attributeName = attribute.text
                    defaultValue = attribute.attrib['default']
                    valueCheck = attribute.attrib['check']
                    isPrimary = True if attribute.attrib['primary'] == 'True' else False
                    if isPrimary:
                        if primaryCount > 0:
                            raise AttributeError('Malformed Entity: ' + entityName + ' - too many primary fields')
                        else:
                            primaryCount += 1
                    if self.runCheckOnAttribute(defaultValue, valueCheck):
                        attributesDict[attributeName] = [attribute.attrib['default'], attribute.attrib['check'],
                                                         isPrimary]
                    else:
                        raise AttributeError('Malformed Entity: ' + entityName + ' - default values do not conform to '
                                             'their corresponding checks.')
                if primaryCount != 1:
                    raise AttributeError('Malformed Entity: ' + entityName + ' - invalid number of primary fields '
                                                                             'specified.')
                icon = entity.find('Icon')
                if icon is not None:
                    icon = icon.text.strip()
                elif icon is None or icon == '':
                    icon = 'Default.svg'
                if self.entityCategoryList.get(category) is None:
                    self.entityCategoryList[category] = {}
                self.entityCategoryList[category][entityName] = {
                    'Attributes': attributesDict,
                    'Icon': str(Path(self.mainWindow.SETTINGS.value("Program/BaseDir")) / "Resources" / "Icons" / icon)}
            except (KeyError, AttributeError) as err:
                # Ignore malformed entities
                self.messageHandler.error('Error: ' + str(err), popUp=False)
                continue
        return True

    def loadCoreEntities(self) -> None:
        entDir = Path(self.mainWindow.SETTINGS.value("Program/BaseDir")) / "Core" / "Entities"
        for entFile in listdir(entDir):
            if entFile.endswith('.xml'):
                self.addRecognisedEntityTypes(entDir / entFile)

    def loadModuleEntities(self) -> None:
        entDir = Path(self.mainWindow.SETTINGS.value("Program/BaseDir")) / "Modules"
        for module in listdir(entDir):
            for entFile in listdir(entDir / module):
                if entFile.endswith('.xml'):
                    self.addRecognisedEntityTypes(
                        entDir / module / entFile)

    def getEntityJson(self, entityType: str, jsonData=None) -> Union[dict, None]:
        eJson = {'uid': str(uuid4())}
        if entityType in self.getAllEntitiesInCategory('Meta'):
            eJson['uid'] += '@'
        try:
            for category in self.entityCategoryList:
                if entityType in self.entityCategoryList[category]:
                    for attribute in self.entityCategoryList[category][entityType]['Attributes']:
                        eJson[attribute] = self.entityCategoryList[category][entityType]['Attributes'][attribute][0]
                    break
        except KeyError:
            self.messageHandler.error("Attempted to get attributes for "
                                      "malformed entity type: " + str(entityType), True)
            return None
        eJson['Entity Type'] = entityType
        eJson['Date Created'] = None
        eJson['Date Last Edited'] = None
        eJson['Notes'] = ""
        eJson['Icon'] = self.getEntityDefaultPicture(entityType)

        if jsonData is not None:
            # Allow setting of attributes that are not defined in the Entity specification.
            for key in jsonData:
                value = jsonData.get(key)
                if value is not None and value != '':
                    eJson[key] = value

        utcNow = datetime.isoformat(datetime.utcnow())
        if eJson['Date Created'] is None:
            eJson['Date Created'] = utcNow
        else:
            # Always make sure dates are in ISO format.
            try:
                eJson['Date Created'] = parser.parse(str(eJson['Date Created'])).isoformat()
            except (TypeError, ValueError):
                eJson['Date Created'] = utcNow

        eJson['Date Last Edited'] = utcNow

        return eJson

    def getPrimaryFieldForEntityType(self, entityType: str) -> Union[str, None]:
        try:
            for category in self.entityCategoryList:
                if entityType in self.entityCategoryList[category]:
                    for attribute in self.entityCategoryList[category][entityType]['Attributes']:
                        if self.entityCategoryList[category][entityType]['Attributes'][attribute][2]:
                            return attribute
        except KeyError:
            self.messageHandler.error("Attempted to get primary attribute for "
                                      "malformed entity type: " + str(entityType), True)
        return None

    def getBareBonesEntityJson(self, entityType: str) -> Union[dict, None]:
        eJson = {}
        try:
            for category in self.entityCategoryList:
                if entityType in self.entityCategoryList[category]:
                    for attribute in self.entityCategoryList[category][entityType]['Attributes']:
                        eJson[attribute] = self.entityCategoryList[category][entityType]['Attributes'][attribute][0]
                    break
        except KeyError:
            self.messageHandler.error("Attempted to get attributes for "
                                      "malformed entity type: " + str(entityType), True)
            return None
        eJson['Entity Type'] = entityType

        return eJson

    def getLinkJson(self, jsonData: dict) -> Union[dict, None]:
        linkJson = {}
        try:
            linkJson['uid'] = jsonData['uid']
        except KeyError:
            return None

        utcNow = datetime.isoformat(datetime.utcnow())
        linkJson['Resolution'] = str(jsonData.get('Resolution'))  # This way, if it is None, it is cast to a string.
        linkJson['Date Created'] = jsonData.get('Date Created')
        # Make sure that dates are always in ISO format.
        if linkJson['Date Created'] is None:
            linkJson['Date Created'] = utcNow
        else:
            try:
                linkJson['Date Created'] = parser.parse(str(linkJson['Date Created'])).isoformat()
            except (TypeError, ValueError):
                linkJson['Date Created'] = utcNow
        linkJson['Date Last Edited'] = utcNow
        linkJson['Notes'] = str(jsonData.get('Notes'))

        # Transfer all values from jsonData to linkJson, but preserve the values and order of linkJson for existing
        #   keys.
        jsonData.update(linkJson)
        linkJson.update(jsonData)

        return linkJson

    def getEntityDefaultPicture(self, entityType) -> QByteArray:
        picture = Path(self.mainWindow.SETTINGS.value("Program/BaseDir")) / "Resources" / "Icons" / "Default.svg"
        try:
            for category in self.entityCategoryList:
                if entityType in self.entityCategoryList[category]:
                    entityPicture = self.entityCategoryList[category][entityType]['Icon']
                    if Path(entityPicture).exists():
                        picture = entityPicture
                    break
        except KeyError:
            self.messageHandler.warning("Attempted to get icon for "
                                        "nonexistent entity type: " + str(entityType), popUp=False)
        finally:
            with open(picture, 'rb') as pictureFile:
                pictureContents = pictureFile.read()
            pictureByteArray = QByteArray(pictureContents)
            return pictureByteArray

    def getLinkPicture(self):
        picture = Path(self.mainWindow.SETTINGS.value("Program/BaseDir")) / "Resources" / "Icons" / "Resolution.png"
        return QIcon(str(picture)).pixmap(40, 40)

    def getLinkArrowPicture(self):
        picture = Path(self.mainWindow.SETTINGS.value("Program/BaseDir")) / "Resources" / "Icons" / "Right-Arrow.svg"
        return QIcon(str(picture)).pixmap(40, 40)

    def deconstructGraph(self, graph: nx.DiGraph) -> tuple:
        nodes = {}
        for nodeKey in graph.nodes:
            # Dereference the original dict so we don't actually convert its icon to data.
            nodes[nodeKey] = dict(graph.nodes.get(nodeKey))
            try:
                nodes[nodeKey]['Icon'] = nodes[nodeKey]['Icon'].toBase64().data()
            except KeyError:
                pass

        edges = {edgeKey: graph.edges.get(edgeKey) for edgeKey in graph.edges}
        return nodes, edges

    def deconstructGraphForFileDump(self, graph: nx.DiGraph) -> tuple:
        nodes = {}
        for nodeKey in graph.nodes:
            # Dereference the original dict so we don't actually convert its icon to data.
            nodes[nodeKey] = dict(graph.nodes.get(nodeKey))
            try:
                nodes[nodeKey]['Icon'] = nodes[nodeKey]['Icon'].toBase64().data()
            except KeyError:
                pass

        edges = {str(edgeKey): graph.edges.get(edgeKey) for edgeKey in graph.edges}
        return nodes, edges

    def reconstructGraphFromString(self, graphString: str) -> tuple:
        nodes, edges = literal_eval(graphString)
        for node in nodes:
            try:
                nodes[node]['Icon'] = QByteArray(b64decode(nodes[node]['Icon']))
            except KeyError:
                pass

        return nodes, edges

    def reconstructGraphFullFromFile(self, graphNodesAndEdges: Union[tuple, list]) -> nx.DiGraph:
        returnGraph = nx.DiGraph()
        graphNodes = graphNodesAndEdges[0]
        graphEdges = graphNodesAndEdges[1]
        for node in graphNodes:
            try:
                graphNodes[node]['Icon'] = QByteArray(b64decode(graphNodes[node]['Icon']))
            except KeyError:
                pass
            returnGraph.add_node(node, **graphNodes[node])

        for edge in graphEdges:
            edgeUID = tuple(literal_eval(edge))
            graphEdges[edge]['uid'] = edgeUID
            returnGraph.add_edge(*edgeUID, **graphEdges[edge])

        return returnGraph
