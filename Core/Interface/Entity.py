#!/usr/bin/env python3

from json import dumps
import math
from typing import Any, Optional

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtWidgets import QGraphicsItemGroup, QGraphicsSimpleTextItem, QGraphicsPixmapItem, QGraphicsTextItem
from PySide6.QtSvgWidgets import QGraphicsSvgItem

ENTITY_TEXT_FONT = QtGui.QFont("Mono", 11, 700)
LINK_TEXT_FONT = QtGui.QFont("Mono", 11, 700)


class BaseNode(QGraphicsItemGroup):

    def __init__(self, pictureByteArray: QtCore.QByteArray, uid, primaryAttribute: str, font: QtGui.QFont,
                 brush: QtGui.QBrush) -> None:
        super(BaseNode, self).__init__()

        self.setCacheMode(self.DeviceCoordinateCache)

        self.pixmapItem = QtGui.QPixmap()
        self.pixmapItem.loadFromData(pictureByteArray)

        if pictureByteArray.data().startswith(b'<svg '):
            self.iconItem = QGraphicsSvgItem()
            self.iconItem.renderer().load(pictureByteArray)
            # Force recalculation of geometry, else this looks like 1 pixel.
            # https://stackoverflow.com/a/68182093
            self.iconItem.setElementId("")
        else:
            self.iconItem = QGraphicsPixmapItem(self.pixmapItem)

        self.labelItem = QGraphicsTextItem('')
        # Have to do it this way; directly assigning stuff does not work due to how PySide6 works.
        labelDocument = self.labelItem.document()
        labelDocument.setTextWidth(280)
        textOption = labelDocument.defaultTextOption()
        textOption.setWrapMode(QtGui.QTextOption.WrapAtWordBoundaryOrAnywhere)
        textOption.setAlignment(QtCore.Qt.AlignHCenter)
        labelDocument.setDefaultTextOption(textOption)
        self.labelItem.setDocument(labelDocument)

        self.addToGroup(self.iconItem)
        self.addToGroup(self.labelItem)
        if font is not None:
            self.labelItem.setFont(font)
        else:
            self.labelItem.setFont(ENTITY_TEXT_FONT)
        if brush is not None:
            self.labelItem.setDefaultTextColor(brush.color())

        self.labelItem.setPos(self.iconItem.x() - 120, self.iconItem.y() + 45)
        self.updateLabel(primaryAttribute)

        self.uid = uid
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        # Check if this option makes the software feel better or worse to use.
        self.setFlag(QGraphicsItem.ItemClipsToShape, True)
        self.setAcceptHoverEvents(True)

        self.connectors = []
        self.bookmarked = False
        self.isBeingResolved = False
        self.parentGroup = None

    def updateLabel(self, newText: str = '') -> None:
        if not isinstance(newText, str):
            newText = str(newText)
        if newText != '':
            if len(newText) > 50:
                newText = newText[:47] + "..."
            self.labelItem.setPlainText(newText)

    def removeConnector(self, connector) -> None:
        # Exception could be thrown if the connector is already deleted.
        try:
            self.connectors.remove(connector)
        except ValueError:
            pass

    def addConnector(self, connector) -> None:
        self.connectors.append(connector)

    def getConnectorByUID(self, uid) -> None:
        for connector in self.connectors:
            if connector.uid == uid:
                return connector

    def hoverEnterEvent(self, event) -> None:
        super().hoverEnterEvent(event)
        self.scene().detailsWidgetCaller(uid=self.uid)

    def hoverLeaveEvent(self, event) -> None:
        super().hoverLeaveEvent(event)
        self.scene().detailsWidgetCaller()

    def mouseDoubleClickEvent(self, event) -> None:
        self.scene().editEntityProperties(self.uid)
        super().mouseDoubleClickEvent(event)

    def shape(self) -> QtGui.QPainterPath:
        returnPath = QtGui.QPainterPath()
        returnPath.addRect(QtCore.QRectF(self.iconItem.x() - 20, self.iconItem.y() - 20, 80, 80))
        return returnPath

    def boundingRect(self) -> QtCore.QRectF:
        return QtCore.QRectF(self.iconItem.x() - 20, self.iconItem.y() - 20, 80, 80)

    def childrenBoundingRect(self) -> QtCore.QRectF:
        return QtCore.QRectF(self.iconItem.x() - 20, self.iconItem.y() - 20, 80, 80)

    def boundingRegion(self, itemToDeviceTransform: QtGui.QTransform) -> QtGui.QRegion:
        return self.iconItem.boundingRegion(itemToDeviceTransform)

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionGraphicsItem,
              widget: Optional[QtWidgets.QWidget] = ...) -> None:
        painter.setPen(QtCore.Qt.NoPen)
        if self.scene().views()[0].zoom < self.scene().hideZoom:
            self.labelItem.hide()
        else:
            self.labelItem.show()
        if self.isSelected():
            centerPoint = QtCore.QPointF(self.iconItem.x() + 20, self.iconItem.y() + 20)
            selectionBackgroundGradient = QtGui.QRadialGradient(centerPoint, 80, centerPoint)
            selectionBackgroundGradient.setColorAt(0.0, QtGui.QColor(250, 250, 255))
            selectionBackgroundGradient.setColorAt(0.5, QtGui.QColor(231, 240, 253, 0))
            painter.setBrush(selectionBackgroundGradient)
            painter.drawRect(QtCore.QRectF(self.iconItem.x() - 20, self.iconItem.y() - 20, 80, 80))
        super(BaseNode, self).paint(painter, option, widget)


class GroupNode(BaseNode):

    # childNodes is a list of tuples, uid and picture, of all the nodes in the group.
    def __init__(self, pictureByteArray, uid: str, label: str = 'Entity Group', font=None, brush=None) -> None:
        super(GroupNode, self).__init__(pictureByteArray, uid, label, font, brush)
        self.groupedNodesConnectors = []
        self.itemsThatWereGrouped = []
        self.groupedNodesUid = set()

        self.listWidget = GroupNodeChildList()
        self.listProxyWidget = None

    def itemChange(self, change: QtWidgets.QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QtWidgets.QGraphicsItem.ItemSelectedChange:
            if value:
                self.showList(None)
            else:
                self.hideList()
        return value

    def showList(self, pos: QtCore.QPoint = None) -> None:
        if self.listWidget is None or self.listProxyWidget is None:
            return
        self.listWidget.itemList.clear()
        for uid in self.groupedNodesUid:
            entityJson = self.scene().parent().entityDB.getEntity(uid)
            try:
                primaryField = entityJson[list(entityJson)[1]]
            except IndexError:
                primaryField = ''
            iconPixmap = QtGui.QPixmap()
            iconPixmap.loadFromData(entityJson['Icon'])

            GroupNodeListItem(icon=iconPixmap, text=primaryField, uid=uid,
                              listview=self.listWidget.itemList)
        if pos is None:
            pos = QtCore.QPoint(self.pos().x() + 60, self.pos().y())
        self.listProxyWidget.setPos(pos)
        self.listProxyWidget.setVisible(True)

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        super(GroupNode, self).mouseMoveEvent(event)
        if self.listProxyWidget is not None and self.listProxyWidget.isVisible():
            self.listProxyWidget.setPos(QtCore.QPoint(self.pos().x() + 60, self.pos().y()))

    def hideList(self) -> None:
        if self.listProxyWidget is not None:
            self.listProxyWidget.hide()
            self.listProxyWidget.setVisible(False)

    def formGroup(self, childNodeUIDs, listProxyWidget: QtWidgets.QGraphicsProxyWidget) -> None:
        [self.addItemToGroup(uid) for uid in childNodeUIDs]  # Should be faster than just a for loop
        self.listProxyWidget = listProxyWidget
        self.listProxyWidget.setCacheMode(self.DeviceCoordinateCache)

    def addItemToGroup(self, uid: str) -> None:
        self.groupedNodesUid.add(uid)
        self.handleAddItemConnectors(uid)

    def handleAddItemConnectors(self, uid) -> None:
        incomingLinks = self.scene().parent().entityDB.getIncomingLinks(uid)
        outgoingLinks = self.scene().parent().entityDB.getOutgoingLinks(uid)

        # Suppress exceptions, as these give false alarms when initially drawing the graph on the canvas.
        for link in incomingLinks:
            self.scene().addLinkProgrammatic(link, self.scene().parent().entityDB.getLink(link)['Resolution'],
                                             suppressNonExistentEntityException=True)
        for link in outgoingLinks:
            self.scene().addLinkProgrammatic(link, self.scene().parent().entityDB.getLink(link)['Resolution'],
                                             suppressNonExistentEntityException=True)

    def removeSpecificItemFromGroupIfExists(self, uid) -> bool:
        if uid in self.groupedNodesUid:
            self.groupedNodesUid.remove(uid)
            self.setSelected(False)
            return True
        return False


# Ref: https://doc.qt.io/qt-5/qtwidgets-graphicsview-diagramscene-example.html#arrow-class-definition
# Ref: https://github.com/PySide/Examples/blob/master/examples/graphicsview/diagramscene/diagramscene.py
class BaseConnector(QGraphicsItemGroup):

    def __init__(self, origin, destination, name: str = 'None', uid=None, parent=None,
                 font: QtGui.QFont = None, brush: QtGui.QBrush = None) -> None:
        super(BaseConnector, self).__init__(parent)

        self.myStartItem = origin
        self.myEndItem = destination

        self.labelItem = QGraphicsSimpleTextItem('')
        self.addToGroup(self.labelItem)
        if font is not None:
            self.labelItem.setFont(font)
        else:
            self.labelItem.setFont(LINK_TEXT_FONT)
        if brush is not None:
            self.labelItem.setBrush(brush)

        self.updateLabel(name)

        if uid is not None:
            if isinstance(uid, list) or isinstance(uid, set):
                self.uid = set(uid)
            else:
                self.uid = {uid}
        else:
            self.uid = {(origin.uid, destination.uid)}

        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.labelItem.setFlag(QGraphicsItem.ItemIsSelectable, False)

        self.setZValue(-100)
        self.myStartItem.addConnector(self)
        self.myEndItem.addConnector(self)

        # Set as the wrong positions to force drawing.
        self.oldStartPos = QtCore.QPointF(self.myStartItem.pos().x() + 1, 0)
        self.oldEndPos = QtCore.QPointF(self.myEndItem.pos().x() + 1, 0)

        self.colorSelected = QtGui.QColor(0, 173, 238)
        self.colorDefault = QtGui.QColor(200, 200, 200)
        self.myColor = self.colorDefault

        self.pen = QtGui.QPen(self.myColor, 2, QtCore.Qt.SolidLine,
                              QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)

        self.arrowHead = QtGui.QPolygonF()
        self.line = QtCore.QLineF()

    def updateLabel(self, newText: str = '') -> None:
        if len(newText) > 50:
            newText = newText[:47] + "..."
        self.labelItem.setText(newText)
        self.update()

    def mousePressEvent(self, event) -> None:
        self.scene().detailsWidgetCaller(uid=self.uid)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if len(self.uid) == 1:
            self.scene().editLinkProperties(next(iter(self.uid)))
        else:
            # This will cause a message to be shown to the user, telling them that links representing multiple
            #   connections cannot be edited.
            self.scene().editLinkProperties("")
        super().mouseDoubleClickEvent(event)

    def startItem(self) -> BaseNode:
        return self.myStartItem

    def endItem(self) -> BaseNode:
        return self.myEndItem

    def updatePosition(self) -> None:
        self.line = QtCore.QLineF(self.mapFromItem(self.myStartItem, 0, 0), self.mapFromItem(self.myEndItem, 0, 0))
        self.update()

    def boundingRect(self) -> QtCore.QRectF:
        extra = self.pen.width() + 20
        p1 = self.line.p1()
        p2 = self.line.p2()
        return QtCore.QRectF(p1, QtCore.QSizeF(p2.x() - p1.x(), p2.y() - p1.y())
                             ).normalized().adjusted(-extra, -extra, extra, extra)

    def shape(self) -> QtGui.QPainterPath:
        path = QtGui.QPainterPath(self.line.p1())
        path.lineTo(self.line.p2())
        path.addPolygon(self.arrowHead)
        return path

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionGraphicsItem,
              widget: Optional[QtWidgets.QWidget] = ...) -> None:

        currentStartPos = self.myStartItem.pos()
        currentEndPos = self.myEndItem.pos()

        self.myColor = self.colorSelected if self.isSelected() else self.colorDefault

        if currentEndPos == self.oldEndPos and currentStartPos == self.oldStartPos:
            myPen = QtGui.QPen(self.myColor)
            painter.setPen(myPen)
            painter.setBrush(self.myColor)
            painter.drawLine(self.line)
            painter.drawPolygon(self.arrowHead)
            if self.scene().views()[0].zoom < self.scene().hideZoom:
                self.labelItem.hide()
            else:
                self.labelItem.show()
            return

        self.oldStartPos = currentStartPos
        self.oldEndPos = currentEndPos

        p1 = QtCore.QPointF(self.myStartItem.pos().x() + 20, self.myStartItem.pos().y() + 20)
        p2 = QtCore.QPointF(self.myEndItem.pos().x() + 20, self.myEndItem.pos().y() + 20)

        line = QtCore.QLineF(p1, p2)

        if line.length() < 45:
            self.labelItem.hide()
            return

        angle = math.atan2(line.dy(), - line.dx())

        if (line.length() < 50 + len(self.labelItem.text()) * 15) or \
                self.scene().views()[0].zoom < self.scene().hideZoom:
            self.labelItem.hide()
        else:
            self.labelItem.show()
            angle2 = math.degrees(math.pi - angle)
            if 90 < angle2 < 270:
                angle2 -= 180
                # When the label flips, it starts from 0.3 and reads towards the starting node (as opposed to
                #   reading towards the ending node).
                # To avoid overlap, we get the proportion of the text to the length of the line, and add it to the
                #   offset of 0.3 to keep the label at the same relative location.
                self.labelItem.setPos(line.pointAt(0.3 + (self.labelItem.boundingRect().width() / line.length())))
            else:
                self.labelItem.setPos(line.pointAt(0.3))
            self.labelItem.setRotation(angle2)

        myPen = QtGui.QPen(self.myColor)
        arrowSize = 20.0
        painter.setPen(myPen)
        painter.setBrush(self.myColor)

        line.setLength(line.length() - 45)
        self.line = line

        arrowP1 = line.p2() + QtCore.QPointF(
            math.sin(angle + math.pi / 3.0) * arrowSize,
            math.cos(angle + math.pi / 3.0) * arrowSize)
        arrowP2 = line.p2() + QtCore.QPointF(
            math.sin(angle + math.pi - math.pi / 3.0) * arrowSize,
            math.cos(angle + math.pi - math.pi / 3.0) * arrowSize)

        self.arrowHead.clear()
        for point in [line.p2(), arrowP1, arrowP2]:
            self.arrowHead.append(point)

        painter.drawLine(line)
        painter.drawPolygon(self.arrowHead)


class GroupNodeListItem(QtWidgets.QListWidgetItem):

    def __init__(self, icon, text, uid: str, listview=None) -> None:
        super(GroupNodeListItem, self).__init__(icon, text, listview)
        self.uid = uid


class GroupNodeChildList(QtWidgets.QWidget):

    def __init__(self) -> None:
        super(GroupNodeChildList, self).__init__()

        self.setLayout(QtWidgets.QVBoxLayout())
        titleLabel = QtWidgets.QLabel('Child Items')
        titleLabel.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter)
        self.layout().addWidget(titleLabel)

        self.itemList = ChildListWidget()
        self.layout().addWidget(self.itemList)


class ChildListWidget(QtWidgets.QListWidget):

    def __init__(self) -> None:
        super(ChildListWidget, self).__init__()
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        itemDragged = self.itemAt(event.pos())

        if itemDragged is None:
            return

        self.setCurrentItem(itemDragged)
        drag = QtGui.QDrag(self)
        mimeData = QtCore.QMimeData()

        mimeData.setText(dumps({'uid': itemDragged.uid}))
        drag.setMimeData(mimeData)

        # All Entities should have icons, but you never know.
        pixmap = None
        if itemDragged.icon() is not None:
            pixmap = itemDragged.icon().pixmap(100, 100)
            drag.setPixmap(pixmap)
        drag.setHotSpot(QtCore.QPoint(pixmap.rect().width() / 2, pixmap.rect().height() / 2))
        drag.exec_()

        super().mousePressEvent(event)
