#!/usr/bin/env python3

import contextlib
from PySide6 import QtWidgets, QtCore, QtCharts, QtGui
from Core.Interface import Stylesheets
from datetime import datetime
from getpass import getuser
import networkx as nx
import queue


class DockBarThree(QtWidgets.QDockWidget):
    """
    Dockbar that hosts the Timeline, Chat and Server Status widgets.
    """

    def initialiseLayout(self):
        # self.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)
        childWidget = QtWidgets.QWidget()
        childWidget.setLayout(QtWidgets.QVBoxLayout())
        childWidget.setContentsMargins(0, 0, 0, 0)
        self.setWidget(childWidget)

        childWidget2 = QtWidgets.QWidget()
        childWidget2.setContentsMargins(0, 0, 0, 0)
        childWidget2.setLayout(QtWidgets.QHBoxLayout())
        childWidget.layout().addWidget(childWidget2)
        childWidget2.layout().addWidget(self.tabPane)
        self.tabPane.setContentsMargins(0, 0, 0, 0)
        self.tabPane.addTab(self.logViewer, 'Program Log')
        self.tabPane.addTab(self.timeWidget, 'Timeline')
        childWidget2.layout().addWidget(self.chatBox)
        self.serverStatus.setStyleSheet(Stylesheets.DOCK_BAR_LABEL)
        childWidget.layout().addWidget(self.serverStatus)

    def __init__(self, mainWindow, title="Dockbar Three"):
        super(DockBarThree, self).__init__(parent=mainWindow)
        self.setAllowedAreas(QtCore.Qt.TopDockWidgetArea |
                             QtCore.Qt.BottomDockWidgetArea)
        self.setFeatures(QtWidgets.QDockWidget.DockWidgetMovable |
                         QtWidgets.QDockWidget.DockWidgetFloatable |
                         QtWidgets.QDockWidget.DockWidgetClosable)
        self.setWindowTitle(title)
        self.setObjectName(title)
        self.setMaximumHeight(275)
        self.setMinimumHeight(275)

        self.tabPane = QtWidgets.QTabWidget()

        self.serverStatus = ServerStatusBox(self)
        self.chatBox = ChatBox(self, self.parent())
        self.timeWidget = TimeWidget(self, self.parent())
        self.logViewer = QtWidgets.QPlainTextEdit()
        self.logViewer.setStyleSheet(Stylesheets.MENUS_STYLESHEET_2)

        # Because we're not going to stop the thread before closing, an error will be thrown by Qt.
        # That error can be safely ignored.
        self.logViewerUpdateThread = LoggingUpdateThread(mainWindow.MESSAGEHANDLER)
        self.logViewerUpdateThread.loggingSignal.connect(self.updateLogs)
        self.logViewerUpdateThread.start()
        self.logViewer.setReadOnly(True)

        self.initialiseLayout()

    def updateLogs(self, newLogMessage: str):
        self.logViewer.appendPlainText(newLogMessage)


class TimeWidget(QtWidgets.QWidget):

    def __init__(self, parent, mainWindow):
        super(TimeWidget, self).__init__(parent=parent)

        self.mainWindow = mainWindow
        self.timeDetails = {}
        self.currentTimeStep = []

        self.timelineChart = QtCharts.QChart()
        self.timelineChart.setTitle("Timeline")
        self.timelineChart.setTheme(QtCharts.QChart.ChartThemeBlueCerulean)
        self.timelineChart.setMargins(QtCore.QMargins(0, 0, 0, 0))
        self.chartView = QtCharts.QChartView(self.timelineChart)
        self.chartView.setRubberBand(QtCharts.QChartView.NoRubberBand)
        self.timelineChart.setAnimationOptions(QtCharts.QChart.AllAnimations)
        self.timelineChart.setAnimationDuration(250)
        self.timelineChart.legend().hide()

        self.timescaleSelector = TimelineTimescaleSelector(self)

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().addWidget(self.timescaleSelector)
        self.layout().addWidget(self.chartView)

    def takePictureOfView(self, transparentBackground: bool = False):
        # Need to set size and format of pic before using it.
        # Ref: https://qtcentre.org/threads/10975-Help-Export-QGraphicsView-to-Image-File
        # Rendering best optimized to rgb32 and argb32_premultiplied.
        # Ref: https://doc.qt.io/qtforpython/PySide6/QtGui/QImage.html?highlight=qimage#image-formats
        picture = QtGui.QImage(self.chartView.size(), QtGui.QImage.Format_ARGB32_Premultiplied)
        # Pictures are initialised with junk data - need to clear it out before painting
        #   to avoid visual artifacts.
        picture.fill(QtGui.QColor(0, 0, 0, 0))
        picturePainter = QtGui.QPainter(picture)
        if not transparentBackground:
            picture.fill(QtGui.QColor(61, 61, 61))
        self.chartView.render(picturePainter)
        return picture

    def updateTimeline(self, node, added: bool = True, updateGraph: bool = True):
        nodeTime = datetime.fromisoformat(node['Date Created'])

        nodeYear = nodeTime.year
        nodeMonth = nodeTime.month
        nodeDay = nodeTime.day
        nodeHour = nodeTime.hour
        nodeMinute = nodeTime.minute

        # Dicts are fast, but this is not very efficient.
        if nodeYear not in self.timeDetails:
            self.timeDetails[nodeYear] = {}

        if nodeMonth not in self.timeDetails[nodeYear]:
            self.timeDetails[nodeYear][nodeMonth] = {}

        if nodeDay not in self.timeDetails[nodeYear][nodeMonth]:
            self.timeDetails[nodeYear][nodeMonth][nodeDay] = {}

        if nodeHour not in self.timeDetails[nodeYear][nodeMonth][nodeDay]:
            self.timeDetails[nodeYear][nodeMonth][nodeDay][nodeHour] = {}

        if nodeMinute not in self.timeDetails[nodeYear][nodeMonth][nodeDay][nodeHour]:
            # Sanity check. Should not be able to remove nodes that do not exist, but you never know.
            self.timeDetails[nodeYear][nodeMonth][nodeDay][nodeHour][nodeMinute] = 1 if added else 0

        elif added:
            self.timeDetails[nodeYear][nodeMonth][nodeDay][nodeHour][nodeMinute] += 1
        elif self.timeDetails[nodeYear][nodeMonth][nodeDay][nodeHour][nodeMinute] > 0:
            self.timeDetails[nodeYear][nodeMonth][nodeDay][nodeHour][nodeMinute] -= 1

        if updateGraph:
            self.drawChart([])

    def resetTimeline(self, graph: nx.DiGraph, updateGraph: bool = True):
        self.timeDetails = {}

        for node in graph.nodes():
            self.updateTimeline(graph.nodes[node], True, False)

        if updateGraph:
            self.drawChart([])

    def drawChart(self, timescale: list):
        try:
            year = timescale[0]
        except IndexError:
            year = None
        try:
            month = timescale[1]
        except IndexError:
            month = None
        try:
            day = timescale[2]
        except IndexError:
            day = None
        try:
            hour = timescale[3]
        except IndexError:
            hour = None
        try:
            minute = timescale[4]
        except IndexError:
            minute = None

        if minute is not None:
            barsDict = {minute: self.timeDetails[year][month][day][hour][minute]}
            self.currentTimeStep = [year, month, day, hour, minute]
        elif hour is not None:
            barsDict = {minute: self.timeDetails[year][month][day][hour][minute]
                        for minute in self.timeDetails[year][month][day][hour]}

            self.currentTimeStep = [year, month, day, hour]
        elif day is not None:
            barsDict = {}
            for hour in self.timeDetails[year][month][day]:
                barsDict[hour] = 0
                for minute in self.timeDetails[year][month][day][hour]:
                    barsDict[hour] += self.timeDetails[year][month][day][hour][minute]
            self.currentTimeStep = [year, month, day]
        elif month is not None:
            barsDict = {}
            for day in self.timeDetails[year][month]:
                barsDict[day] = 0
                for hour in self.timeDetails[year][month][day]:
                    for minute in self.timeDetails[year][month][day][hour]:
                        barsDict[day] += self.timeDetails[year][month][day][hour][minute]
            self.currentTimeStep = [year, month]
        elif year is not None:
            barsDict = {}
            for month in self.timeDetails[year]:
                barsDict[month] = 0
                for day in self.timeDetails[year][month]:
                    for hour in self.timeDetails[year][month][day]:
                        for minute in self.timeDetails[year][month][day][hour]:
                            barsDict[month] += self.timeDetails[year][month][day][hour][minute]
            self.currentTimeStep = [year]
        else:
            barsDict = {}
            for year in self.timeDetails:
                barsDict[year] = 0
                for month in self.timeDetails[year]:
                    for day in self.timeDetails[year][month]:
                        for hour in self.timeDetails[year][month][day]:
                            for minute in self.timeDetails[year][month][day][hour]:
                                barsDict[year] += self.timeDetails[year][month][day][hour][minute]
            self.currentTimeStep = []

        self.drawChartHelper(barsDict, self.currentTimeStep)

    def drawChartHelper(self, barsDict: dict, timestep: list):
        timelineSeries = QtCharts.QBarSeries(self.timelineChart)
        maxEntityNum = 0
        xAxisValues = []

        barSet = TimelineBarSet('Entities', self, timestep, list(barsDict))
        barSet.setColor(QtGui.Qt.darkCyan)
        for bar in barsDict:
            barSet.append(barsDict[bar])
            timelineSeries.append(barSet)
            if barsDict[bar] > maxEntityNum:
                maxEntityNum = barsDict[bar]
            value = ""
            for step, stepValue in enumerate(timestep):
                if step <= 2:
                    value += f'{str(stepValue)}/'
                    if step == 2:
                        value = f"{value[:-1]} "
                else:
                    value += f'{str(stepValue)}:'
            value += str(bar)
            xAxisValues.append(value)
        self.timelineChart.removeAllSeries()
        self.timelineChart.addSeries(timelineSeries)
        self.timelineChart.createDefaultAxes()
        self.timelineChart.removeAxis(self.timelineChart.axisX(timelineSeries))
        self.timelineChart.removeAxis(self.timelineChart.axisY(timelineSeries))

        yAxis = QtCharts.QValueAxis()
        yAxis.setTickCount(min(maxEntityNum + 1, 4))

        xAxis = QtCharts.QBarCategoryAxis()
        xAxis.append(xAxisValues)
        self.timelineChart.setAxisY(yAxis, timelineSeries)
        self.timelineChart.setAxisX(xAxis, timelineSeries)

        timesteps = len(timestep)
        if timesteps == 0:
            self.timescaleSelector.adjustLabelsToYear()
        elif timesteps == 1:
            self.timescaleSelector.adjustLabelsToMonth()
        elif timesteps == 2:
            self.timescaleSelector.adjustLabelsToDay()
        elif timesteps == 3:
            self.timescaleSelector.adjustLabelsToHour()
        elif timesteps == 4:
            self.timescaleSelector.adjustLabelsToMinute()
        else:
            self.timescaleSelector.adjustLabelsToSecond()

        yAxis.applyNiceNumbers()
        self.mainWindow.timelineSelectMatchingEntities(timestep)


class TimelineBarSet(QtCharts.QBarSet):

    def __init__(self, label: str, timeWidget: TimeWidget, timestep: list, barSeriesDict: list):
        super(TimelineBarSet, self).__init__(label)

        self.clicked.connect(self.selectedAction)
        self.timeWidget = timeWidget
        self.timestep = timestep
        self.barSeriesDict = barSeriesDict

    def selectedAction(self, index):
        self.timestep.append(self.barSeriesDict[index])
        self.timeWidget.drawChart(self.timestep)


class TimelineTimescaleSelector(QtWidgets.QLabel):

    def __init__(self, timeWidget: TimeWidget):
        super(TimelineTimescaleSelector, self).__init__(parent=timeWidget)
        self.setStyleSheet("""border: 2px solid rgb(44, 49, 58);""")

        self.timeWidget = timeWidget
        self.setMinimumWidth(150)
        self.setMaximumHeight(150)

        self.setLayout(QtWidgets.QFormLayout())
        self.setFrameStyle(QtWidgets.QFrame.Sunken)

        self.yearButton = QtWidgets.QPushButton(' Year: ')
        self.yearButton.clicked.connect(self.yearButtonPressed)
        self.yearText = QtWidgets.QLabel('-')
        self.yearText.setFrameStyle(QtWidgets.QFrame.Sunken)
        self.monthButton = QtWidgets.QPushButton(' Month: ')
        self.monthButton.clicked.connect(self.monthButtonPressed)
        self.monthText = QtWidgets.QLabel('X')
        self.monthText.setFrameStyle(QtWidgets.QFrame.Sunken)
        self.dayButton = QtWidgets.QPushButton(' Day: ')
        self.dayButton.clicked.connect(self.dayButtonPressed)
        self.dayText = QtWidgets.QLabel('X')
        self.dayText.setFrameStyle(QtWidgets.QFrame.Sunken)
        self.hourButton = QtWidgets.QPushButton(' Hour: ')
        self.hourButton.clicked.connect(self.hourButtonPressed)
        self.hourText = QtWidgets.QLabel('X')
        self.hourText.setFrameStyle(QtWidgets.QFrame.Sunken)
        self.minuteButton = QtWidgets.QPushButton(' Minute: ')
        self.minuteButton.clicked.connect(self.minuteButtonPressed)
        self.minuteText = QtWidgets.QLabel('X')
        self.minuteText.setFrameStyle(QtWidgets.QFrame.Sunken)

        self.layout().addRow(self.yearButton, self.yearText)
        self.layout().addRow(self.monthButton, self.monthText)
        self.layout().addRow(self.dayButton, self.dayText)
        self.layout().addRow(self.hourButton, self.hourText)
        self.layout().addRow(self.minuteButton, self.minuteText)

        self.yearButton.setDown(True)
        self.yearButton.setDisabled(True)
        self.monthButton.setDisabled(True)
        self.dayButton.setDisabled(True)
        self.hourButton.setDisabled(True)
        self.minuteButton.setDisabled(True)

    def yearButtonPressed(self):
        self.timeWidget.drawChart(self.timeWidget.currentTimeStep[:0])
        self.adjustLabelsToYear()

    def adjustLabelsToYear(self):
        self.yearButton.setDown(True)
        self.yearButton.setDisabled(True)
        self.monthButton.setDisabled(True)
        self.monthButton.setDown(False)
        self.dayButton.setDisabled(True)
        self.dayButton.setDown(False)
        self.hourButton.setDisabled(True)
        self.hourButton.setDown(False)
        self.minuteButton.setDown(False)
        self.minuteButton.setDisabled(True)

        self.yearText.setText('-')
        self.monthText.setText('X')
        self.dayText.setText('X')
        self.hourText.setText('X')
        self.minuteText.setText('X')

    def monthButtonPressed(self):
        self.timeWidget.drawChart(self.timeWidget.currentTimeStep[:1])
        self.adjustLabelsToMonth()

    def adjustLabelsToMonth(self):
        self.yearButton.setDown(False)
        self.yearButton.setDisabled(False)
        self.monthButton.setDown(True)
        self.monthButton.setDisabled(True)
        self.dayButton.setDisabled(True)
        self.dayButton.setDown(False)
        self.hourButton.setDisabled(True)
        self.hourButton.setDown(False)
        self.minuteButton.setDown(False)
        self.minuteButton.setDisabled(True)

        self.yearText.setText(str(self.timeWidget.currentTimeStep[0]))
        self.monthText.setText('-')
        self.dayText.setText('X')
        self.hourText.setText('X')
        self.minuteText.setText('X')

    def dayButtonPressed(self):
        self.timeWidget.drawChart(self.timeWidget.currentTimeStep[:2])
        self.adjustLabelsToDay()

    def adjustLabelsToDay(self):
        self.yearButton.setDown(False)
        self.yearButton.setDisabled(False)
        self.monthButton.setDown(False)
        self.monthButton.setDisabled(False)
        self.dayButton.setDown(True)
        self.dayButton.setDisabled(True)
        self.hourButton.setDisabled(True)
        self.hourButton.setDown(False)
        self.minuteButton.setDown(False)
        self.minuteButton.setDisabled(True)

        self.yearText.setText(str(self.timeWidget.currentTimeStep[0]))
        self.monthText.setText(str(self.timeWidget.currentTimeStep[1]))
        self.dayText.setText('-')
        self.hourText.setText('X')
        self.minuteText.setText('X')

    def hourButtonPressed(self):
        self.timeWidget.drawChart(self.timeWidget.currentTimeStep[:3])
        self.adjustLabelsToHour()

    def adjustLabelsToHour(self):
        self.yearButton.setDown(False)
        self.yearButton.setDisabled(False)
        self.monthButton.setDown(False)
        self.monthButton.setDisabled(False)
        self.dayButton.setDown(False)
        self.dayButton.setDisabled(False)
        self.hourButton.setDown(True)
        self.hourButton.setDisabled(True)
        self.minuteButton.setDown(False)
        self.minuteButton.setDisabled(True)
        self.yearText.setText(str(self.timeWidget.currentTimeStep[0]))
        self.monthText.setText(str(self.timeWidget.currentTimeStep[1]))
        self.dayText.setText(str(self.timeWidget.currentTimeStep[2]))
        self.hourText.setText('-')
        self.minuteText.setText('X')

    def minuteButtonPressed(self):
        self.timeWidget.drawChart(self.timeWidget.currentTimeStep[:4])
        self.adjustLabelsToMinute()

    def adjustLabelsToMinute(self):
        self.yearButton.setDown(False)
        self.yearButton.setDisabled(False)
        self.monthButton.setDown(False)
        self.monthButton.setDisabled(False)
        self.dayButton.setDown(False)
        self.dayButton.setDisabled(False)
        self.hourButton.setDown(False)
        self.hourButton.setDisabled(False)
        self.minuteButton.setDown(True)
        self.minuteButton.setDisabled(True)
        self.yearText.setText(str(self.timeWidget.currentTimeStep[0]))
        self.monthText.setText(str(self.timeWidget.currentTimeStep[1]))
        self.dayText.setText(str(self.timeWidget.currentTimeStep[2]))
        self.hourText.setText(str(self.timeWidget.currentTimeStep[3]))
        self.minuteText.setText('-')

    def adjustLabelsToSecond(self):
        self.yearButton.setDown(False)
        self.yearButton.setDisabled(False)
        self.monthButton.setDown(False)
        self.monthButton.setDisabled(False)
        self.dayButton.setDown(False)
        self.dayButton.setDisabled(False)
        self.hourButton.setDown(False)
        self.hourButton.setDisabled(False)
        self.minuteButton.setDown(False)
        self.minuteButton.setDisabled(False)
        self.yearText.setText(str(self.timeWidget.currentTimeStep[0]))
        self.monthText.setText(str(self.timeWidget.currentTimeStep[1]))
        self.dayText.setText(str(self.timeWidget.currentTimeStep[2]))
        self.hourText.setText(str(self.timeWidget.currentTimeStep[3]))
        self.minuteText.setText(str(self.timeWidget.currentTimeStep[4]))


class ServerStatusBox(QtWidgets.QLabel):

    def __init__(self, parent):
        super(ServerStatusBox, self).__init__(parent=parent)
        self.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        self.setFrameStyle(QtWidgets.QFrame.Sunken | QtWidgets.QFrame.StyledPanel)
        self.setText("Not connected to a server")

    def updateStatus(self, status: str):
        self.setText(status)


class ChatBox(QtWidgets.QWidget):
    """
    Sends chat messages to everyone connected to the same server.
    """

    def receiveMessage(self, message: str):
        self.textView.appendPlainText(message)

    def __init__(self, parent, mainWindow):
        super().__init__(parent=parent)

        self.mainWindow = mainWindow
        self.setMinimumWidth(500)
        self.setMaximumWidth(500)

        self.chatName = f"{getuser()}: "

        chatLayout = QtWidgets.QGridLayout()
        self.setLayout(chatLayout)

        chatLabel = QtWidgets.QLabel('Project Collaboration Chat')
        chatLabel.setStyleSheet(Stylesheets.DOCK_BAR_LABEL)
        chatLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.textView = QtWidgets.QPlainTextEdit()
        self.textView.setReadOnly(True)
        self.textSendBox = QtWidgets.QLineEdit()
        self.textSendBox.setPlaceholderText("Type a message to send...")
        self.textSendButton = QtWidgets.QPushButton(" Send ")
        self.textSendButton.clicked.connect(self.sendMessage)

        chatLayout.addWidget(chatLabel, 0, 0, 1, 2)
        chatLayout.addWidget(self.textView, 1, 0, 1, 2)
        chatLayout.addWidget(self.textSendBox, 2, 0)
        chatLayout.addWidget(self.textSendButton, 2, 1)

    def sendMessage(self):
        self.mainWindow.sendChatMessage(self.chatName + self.textSendBox.text())
        self.receiveMessage(self.chatName + self.textSendBox.text())
        self.textSendBox.setText("")


class LoggingUpdateThread(QtCore.QThread):
    loggingSignal = QtCore.Signal(str)
    endLogging = False

    def __init__(self, messageHandler):
        super().__init__()
        self.messageHandler = messageHandler

    def run(self):
        while not self.endLogging:
            if not self.messageHandler.logQueue.empty():
                with contextlib.suppress(queue.Empty):
                    logMsg = self.messageHandler.logQueue.get().getMessage()
                    self.loggingSignal.emit(logMsg)
            else:
                self.msleep(100)
