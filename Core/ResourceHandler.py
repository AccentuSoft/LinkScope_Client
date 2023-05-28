#!/usr/bin/env python3


import contextlib
import re
from typing import Union, Optional
from glob import glob

import networkx as nx
from datetime import timezone
from defusedxml.ElementTree import parse
from datetime import datetime
from os import listdir
from pathlib import Path
from uuid import uuid4
from ast import literal_eval
from base64 import b64decode
from dateutil import parser

from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QSize, QUrl, Qt
from PySide6 import QtWidgets, QtGui


def resizePictureFromBuffer(picBuffer: QByteArray, newSize: tuple) -> QByteArray:
    """
    newSize: First is width, second is height.
    """
    originalImage = QtGui.QImage()
    originalImage.loadFromData(picBuffer)
    newImage = originalImage.scaled(newSize[0], newSize[1])

    pictureByteArray = QByteArray()
    imageBuffer = QBuffer(pictureByteArray)
    imageBuffer.open(QIODevice.OpenModeFlag.WriteOnly)
    newImage.save(imageBuffer, "PNG")
    imageBuffer.close()

    return pictureByteArray


class ResourceHandler:

    def getIcon(self, iconName: str):
        return self.icons[iconName]

    # Load all resources needed.
    def __init__(self, mainWindow) -> None:
        self.mainWindow = mainWindow
        self.programBaseDirPath = Path(self.mainWindow.SETTINGS.value("Program/BaseDir"))
        self.entityCategoryList = {}
        self.moduleAssetPaths = []

        self.icons = {"uploading": str(self.programBaseDirPath / "Resources" / "Icons" / "Uploading.png"),
                      "uploaded": str(self.programBaseDirPath / "Resources" / "Icons" / "Uploaded.png"),
                      "upArrow": str(self.programBaseDirPath / "Resources" / "Icons" / "UpArrow.png"),
                      "downArrow": str(self.programBaseDirPath / "Resources" / "Icons" / "DownArrow.png"),
                      "isolatedNodes": str(self.programBaseDirPath / "Resources" / "Icons" / "SelectIsolated.png"),
                      "addCanvas": str(self.programBaseDirPath / "Resources" / "Icons" / "Add_Canvas.png"),
                      "generateReport": str(self.programBaseDirPath / "Resources" / "Icons" / "Generate_Report.png"),
                      "leafNodes": str(self.programBaseDirPath / "Resources" / "Icons" / "SelectLeaf.png"),
                      "nonIsolatedNodes": str(self.programBaseDirPath / "Resources" / "Icons" /
                                              "SelectNonIsolated.png"),
                      "rootNodes": str(self.programBaseDirPath / "Resources" / "Icons" / "SelectRoot.png"),
                      "split": str(self.programBaseDirPath / "Resources" / "Icons" / "Split.png"),
                      "merge": str(self.programBaseDirPath / "Resources" / "Icons" / "Merge.png"),
                      "shortestPath": str(self.programBaseDirPath / "Resources" / "Icons" / "ShortestPath.png"),
                      "drawLink": str(self.programBaseDirPath / "Resources" / "Icons" / "DrawLink.png"),
                      "rearrange": str(self.programBaseDirPath / "Resources" / "Icons" / "RearrangeGraph.png"),
                      "colorPicker": str(self.programBaseDirPath / "Resources" / "Icons" / "ColorPicker.png"),
                      }

        self.banners = {f"{bannerPath.split('Banner_')[-1].split('.')[0]}": str(bannerPath)
                        for bannerPath in glob(str(self.programBaseDirPath / "Resources" / "Icons" / "Banner_*.svg"))}
        # These are not meant to be strict - just restrictive enough such that users don't put in utter nonsense.
        # Note that regex isn't always the best way of validating fields, but it should be good enough for our
        #   purposes.
        self.checks = {'Email': re.compile(
            r"""(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)])"""),
            'Phonenumber': re.compile(r"""^(\+|00)?[0-9() \-]{3,32}$"""),
            'String': re.compile(r""".+"""),
            'URL': re.compile(r"""[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_+.~#?&/=]*)"""),
            'Onion': re.compile(r"""^https?://\w{56}\.onion/?(\S(?<!\.))*(\.(\S(?<!\.))*)?$"""),
            'Domain': re.compile(r"""^(\S(?<!\.)(?!/)(?<!/)){1,63}(\.(\S(?<!\.)(?!/)(?<!/)){1,63})+$"""),
            'Float': re.compile(r"""^([-+])?(\d|\.(?=\d))+$"""),
            'WordString': re.compile(r"""^\D+$"""),
            'Numbers': re.compile(r"""^\d+$"""),
            'IPv4': re.compile(r"""^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)(\.(?!$)|$)){4}$"""),
            'IPv6': re.compile(
                r"""^(([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]+|::(ffff(:0{1,4})?:)?((25[0-5]|(2[0-4]|1?[0-9])?[0-9])\.){3}(25[0-5]|(2[0-4]|1?[0-9])?[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1?[0-9])?[0-9])\.){3}(25[0-5]|(2[0-4]|1?[0-9])?[0-9]))$"""),
            'MAC': re.compile(r"""^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"""),
            'ASN': re.compile(r"""^(AS)?\d+$"""),
            'CUSIP': re.compile(r"""^[a-zA-Z0-9]{9}$"""),
            'EIN': re.compile(r"""^\d{2}-?\d{7}$"""),
            'LEIID': re.compile(r"""^[a-zA-Z0-9]{20}$"""),
            'ISINID': re.compile(r"""^[a-zA-Z0-9]{2}-?[a-zA-Z0-9]{9}-?[a-zA-Z0-9]$"""),
            'SIC/NAICS': re.compile(r"""^[0-9]{4,6}$""")}

        self.loadModuleEntities(self.programBaseDirPath / "Core" / "Entities")

    def getPictureFromFile(self, filePath: Path, resize: tuple = (0, 0)) -> Optional[QByteArray]:
        """
        resize: tuple, first is width, second is height.
        """
        try:
            with open(filePath, 'rb') as newIconFile:
                fileContents = newIconFile.read()
            if fileContents.startswith(b'<svg ') or fileContents.startswith(b'<?xml '):
                if resize != (0, 0):
                    fileContents = self.resizeSVG(fileContents, resize)
                pictureByteArray = QByteArray(fileContents)
            else:
                image = Image.open(str(filePath))
                if resize != (0, 0):
                    thumbnail = ImageQt(image.resize(resize))
                else:
                    thumbnail = ImageQt(image)
                pictureByteArray = QByteArray()
                imageBuffer = QBuffer(pictureByteArray)

                imageBuffer.open(QIODevice.OpenModeFlag.WriteOnly)

                thumbnail.save(imageBuffer, "PNG")
                imageBuffer.close()
        except ValueError as ve:
                # Image type is unsupported (for ImageQt)
                # Supported types: 1, L, P, RGB, RGBA
                self.mainWindow.MESSAGEHANDLER.warning(f'Invalid Image selected: {str(ve)}', popUp=True)
                pictureByteArray = None

        return pictureByteArray

    def resizeSVG(self, byteString: bytes, resize: tuple):
        bytesWidth = str(resize[0]).encode('UTF-8')
        bytesHeight = str(resize[1]).encode('UTF-8')
        widthRegex = re.compile(b' width="\d*" ')
        for widthMatches in widthRegex.findall(byteString):
            byteString = byteString.replace(widthMatches, b' ')
        heightRegex = re.compile(b' height="\d*" ')
        for heightMatches in heightRegex.findall(byteString):
            byteString = byteString.replace(heightMatches, b' ')
        return byteString.replace(b'<svg ', b'<svg height="%b" width="%b" ' % (bytesHeight, bytesWidth), 1)

    def getEntityCategories(self) -> list:
        return list(self.entityCategoryList)

    def getAllEntityDetailsWithIconsInCategory(self, category) -> list:
        eList = []
        for entity in self.entityCategoryList[category]:
            entityValue = self.entityCategoryList[category][entity]
            eList.append((self.getBareBonesEntityJson(entity),
                          entityValue['Icon']))
        return eList

    def getEntityAttributes(self, entityType) -> Union[None, list]:
        aList = []
        try:
            for category in self.entityCategoryList:
                if entityType in self.entityCategoryList[category]:
                    aList.extend(iter(self.entityCategoryList[category][entityType]['Attributes']))
                    break
        except KeyError:
            self.mainWindow.MESSAGEHANDLER.error(
                f"Attempted to get attributes for nonexistent entity type: {entityType}", True)
            return None
        return aList

    def getAllEntitiesInCategory(self, category) -> list:
        """
        Get all Entity Types in the specified category.
        """
        return list(self.entityCategoryList[category])

    def getCategoryOfEntityType(self, entityType: Union[str, None]):
        return next((category for category in self.entityCategoryList
                     if entityType in self.entityCategoryList[category]),
                    None)

    def getAllEntities(self) -> list:
        """
        Get all recognised Entity Types.
        """
        eList = []
        for category in self.getEntityCategories():
            eList.extend(iter(self.getAllEntitiesInCategory(category)))
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
                            return f'Bad value: {str(attrValue)}'
        except Exception:
            return False
        return True

    def runCheckOnAttribute(self, attribute: str, check: str) -> bool:
        """
        Check that the attribute value given matches the regex of the category 'check'.
        """
        # Ignore checks - this is used for non-string attributes in special entities.
        if check == 'None':
            return True
        attrCheck = self.checks.get(check)
        if attrCheck is None:
            return False
        result = attrCheck.findall(attribute)
        return len(result) == 1

    def getIconPathForIconFile(self, iconFile: str) -> Union[None, Path]:
        iconPath = self.programBaseDirPath / "Resources" / "Icons" / iconFile
        if iconPath.exists():
            return iconPath
        for assetPath in self.moduleAssetPaths:
            iconPath = assetPath / iconFile
            if iconPath.exists():
                return iconPath
        return self.programBaseDirPath / "Resources" / "Icons" / "Default.svg"

    def addRecognisedEntityTypes(self, entityFile: Path) -> list:
        entityTypesAdded = []
        try:
            tree = parse(entityFile, forbid_dtd=True, forbid_entities=True, forbid_external=True)
        except Exception as exc:
            self.mainWindow.MESSAGEHANDLER.warning(
                f'Error occurred when loading entities from {entityFile}: {exc}, skipping.')
            return []

        root = tree.getroot()

        category = root.tag.replace('_', ' ')
        for entity in list(root):
            try:
                entityName = entity.tag.replace('_', ' ')
                attributes = entity.find('Attributes')
                primaryCount = 0
                attributesDict = {}
                for attribute in list(attributes):
                    defaultValue = attribute.attrib['default']
                    valueCheck = attribute.attrib['check']
                    isPrimary = attribute.attrib['primary'] == 'True'
                    if isPrimary:
                        if primaryCount > 0:
                            raise AttributeError(f'Malformed Entity: {entityName} - too many primary fields')
                        else:
                            primaryCount += 1
                    if not self.runCheckOnAttribute(defaultValue, valueCheck):
                        raise AttributeError(f'Malformed Entity: {entityName} - default values do not pass their '
                                             f'corresponding checks.')
                    attributeName = attribute.text
                    attributesDict[attributeName] = [attribute.attrib['default'], attribute.attrib['check'], isPrimary]
                if primaryCount != 1:
                    raise AttributeError(f'Malformed Entity: {entityName} - invalid number of primary fields '
                                         f'specified.')

                icon = entity.find('Icon')
                icon = icon.text.strip() if icon is not None else 'Default.svg'
                if self.entityCategoryList.get(category) is None:
                    self.entityCategoryList[category] = {}
                self.entityCategoryList[category][entityName] = {
                    'Attributes': attributesDict,
                    'Icon': str(self.getIconPathForIconFile(icon))}
                entityTypesAdded.append(f'{category}/{entityName}')
            except (KeyError, AttributeError) as err:
                # Ignore malformed entities
                self.mainWindow.MESSAGEHANDLER.error(f'Error: {str(err)}', popUp=False)
                continue
        return entityTypesAdded

    def loadModuleEntities(self, modulePath: Path) -> list:
        allModuleEntitiesAdded = []
        self.moduleAssetPaths.append(modulePath / "assets")
        for entFile in listdir(modulePath):
            if entFile.endswith('.xml'):
                allModuleEntitiesAdded += self.addRecognisedEntityTypes(modulePath / entFile)
        return allModuleEntitiesAdded

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
            self.mainWindow.MESSAGEHANDLER.error(
                f"Attempted to get attributes for malformed entity type: {entityType}", True)
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

        utcNow = datetime.isoformat(datetime.now(timezone.utc))
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
            self.mainWindow.MESSAGEHANDLER.error(
                f"Attempted to get primary attribute for malformed entity type: {entityType}", True)
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
            self.mainWindow.MESSAGEHANDLER.error(
                f"Attempted to get attributes for malformed entity type: {entityType}", True)
            return None
        eJson['Entity Type'] = entityType

        return eJson

    def getLinkJson(self, jsonData: dict) -> Union[dict, None]:
        linkJson = {}
        try:
            linkJson['uid'] = jsonData['uid']
        except KeyError:
            return None

        utcNow = datetime.isoformat(datetime.now(timezone.utc))
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
        linkJson['Notes'] = str(jsonData.get('Notes', ""))

        # Transfer all values from jsonData to linkJson, but preserve the values and order of linkJson for existing
        #   keys.
        jsonData |= linkJson
        linkJson |= jsonData

        return linkJson

    def getEntityDefaultPicture(self, entityType: str) -> QByteArray:
        picture = self.programBaseDirPath / "Resources" / "Icons" / "Default.svg"
        try:
            for category in self.entityCategoryList:
                if entityType in self.entityCategoryList[category]:
                    entityPicture = self.entityCategoryList[category][entityType]['Icon']
                    if Path(entityPicture).exists():
                        picture = entityPicture
                    break
        except KeyError:
            self.mainWindow.MESSAGEHANDLER.warning(
                f"Attempted to get icon for nonexistent entity type: {entityType}", popUp=False)
        finally:
            with open(picture, 'rb') as pictureFile:
                pictureContents = pictureFile.read()
            return QByteArray(pictureContents)

    def getLinkPicture(self):
        picture = self.programBaseDirPath / "Resources" / "Icons" / "Resolution.png"
        return QtGui.QIcon(str(picture)).pixmap(40, 40)

    def getLinkArrowPicture(self):
        picture = self.programBaseDirPath / "Resources" / "Icons" / "Right-Arrow.svg"
        return QtGui.QIcon(str(picture)).pixmap(40, 40)

    def deconstructGraph(self, graph: nx.DiGraph) -> tuple:
        nodes = {}
        for nodeKey in graph.nodes:
            # Dereference the original dict, so we don't actually convert its icon to data.
            nodes[nodeKey] = dict(graph.nodes.get(nodeKey))
            with contextlib.suppress(KeyError):
                nodes[nodeKey]['Icon'] = nodes[nodeKey]['Icon'].toBase64().data()
        edges = {edgeKey: graph.edges.get(edgeKey) for edgeKey in graph.edges}
        return nodes, edges

    def deconstructGraphForFileDump(self, graph: nx.DiGraph) -> tuple:
        nodes = {}
        for nodeKey in graph.nodes:
            # Dereference the original dict, so we don't actually convert its icon to data.
            nodes[nodeKey] = dict(graph.nodes.get(nodeKey))
            with contextlib.suppress(KeyError):
                nodes[nodeKey]['Icon'] = nodes[nodeKey]['Icon'].toBase64().data()
        edges = {str(edgeKey): graph.edges.get(edgeKey) for edgeKey in graph.edges}
        return nodes, edges

    def reconstructGraphFromString(self, graphString: str) -> tuple:
        nodes, edges = literal_eval(graphString)
        for node in nodes:
            with contextlib.suppress(KeyError):
                nodes[node]['Icon'] = QByteArray(b64decode(nodes[node]['Icon']))
        return nodes, edges

    def reconstructGraphFullFromFile(self, graphNodesAndEdges: Union[tuple, list]) -> nx.DiGraph:
        returnGraph = nx.DiGraph()
        graphNodes = graphNodesAndEdges[0]
        graphEdges = graphNodesAndEdges[1]
        for node in graphNodes:
            with contextlib.suppress(KeyError):
                graphNodes[node]['Icon'] = QByteArray(b64decode(graphNodes[node]['Icon']))
            returnGraph.add_node(node, **graphNodes[node])

        for edge in graphEdges:
            edgeUID = tuple(literal_eval(edge))
            graphEdges[edge]['uid'] = edgeUID
            returnGraph.add_edge(*edgeUID, **graphEdges[edge])

        return returnGraph


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
                                                     options=QtWidgets.QFileDialog.Option.DontUseNativeDialog)
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
            if option == defaultOption:
                radioButton.setChecked(True)
            else:
                radioButton.setChecked(False)
            self.options.append(radioButton)
            vboxLayout.addWidget(radioButton)

    def getValue(self):
        return next((option.text() for option in self.options if option.isChecked()), '')


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
            if option in defaultOptions:
                checkBox.setChecked(True)
            else:
                checkBox.setChecked(False)
            self.options.append(checkBox)
            vboxLayout.addWidget(checkBox)

    def getValue(self):
        return [option.text() for option in self.options if option.isChecked()]


class MinSizeStackedLayout(QtWidgets.QStackedLayout):
    """
    Resize the layout to always take up the appropriate space for the currently selected widget.
    Otherwise, large widgets (due to selecting entities with long strings of text) will stretch
    out the ScrollArea and make the other, non-selected widgets to look bad when the layout
    switches over.

    https://stackoverflow.com/a/34300567
    """

    def sizeHint(self) -> QSize:
        return self.currentWidget().sizeHint()

    def minimumSize(self) -> QSize:
        return self.currentWidget().minimumSize()


class RichNotesEditor(QtWidgets.QTextBrowser):

    def __init__(self, parent=None, currentText: str = '#### Type notes here.\n', allowEditing: bool = True):
        super(RichNotesEditor, self).__init__(parent=parent)
        self.allowEditing = allowEditing
        self.setReadOnly(True)
        if allowEditing:
            self.setUndoRedoEnabled(True)
            self.setTextInteractionFlags(Qt.TextBrowserInteraction | Qt.TextSelectableByKeyboard)
        else:
            self.setUndoRedoEnabled(False)
            self.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
                                         | Qt.LinksAccessibleByMouse | Qt.LinksAccessibleByKeyboard)

        self.contents = currentText
        self.setMarkdown(self.contents)
        self.textFormat = self.currentCharFormat()

    def startEditing(self) -> None:
        if self.allowEditing and self.isReadOnly():
            # Reset char format to plain text.
            self.setCurrentCharFormat(self.textFormat)
            self.setPlainText(self.contents)
            self.setReadOnly(False)

    def stopEditing(self) -> None:
        if not self.isReadOnly():
            self.contents = self.toPlainText()
            self.setMarkdown(self.contents)
            self.setReadOnly(True)

    def dropEvent(self, e: QtGui.QDropEvent) -> None:
        if self.allowEditing:
            editingBefore = self.isReadOnly()
            self.startEditing()
            super(RichNotesEditor, self).dropEvent(e)
            if editingBefore:
                self.stopEditing()

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        potentialLink = self.anchorAt(ev.pos())
        if not potentialLink and ev.button() == QtGui.Qt.MouseButton.LeftButton:
            self.startEditing()
        super(RichNotesEditor, self).mousePressEvent(ev)

    def focusOutEvent(self, ev: QtGui.QFocusEvent) -> None:
        if not self.underMouse() and self.isActiveWindow():
            self.stopEditing()
        super(RichNotesEditor, self).focusOutEvent(ev)

    def doSetSource(self, name: Union[QUrl, str], resourceType: QtGui.QTextDocument.ResourceType = ...) -> None:
        QtGui.QDesktopServices.openUrl(name)
