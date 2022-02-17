#!/usr/bin/env python3

import logging
from logging import handlers

from multiprocessing import Queue
from pathlib import Path
from PySide6 import QtWidgets
from Core.Interface import Stylesheets


class MessageHandler:
    """
    Class that handles logging.
    Requires a parent object which implements a 'getSettings' function
      that returns a Settings object.
    Call 'debug', 'info', 'warning', 'error' or 'critical' depending
      on severity.
    """

    def debug(self, message, exc_info=True):
        self.linkScopeLogger.debug(message, exc_info=exc_info)
        return message

    def info(self, message, popUp=False, exc_info=False):
        self.linkScopeLogger.info(message, exc_info=exc_info)
        if popUp:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)
            QtWidgets.QMessageBox.information(msgBox,
                                              self.mainWindow.tr("Info"),
                                              self.mainWindow.tr(message))
        return message

    def warning(self, message, popUp=False, exc_info=False):
        self.linkScopeLogger.warning(message, exc_info=exc_info)
        if popUp:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)
            QtWidgets.QMessageBox.warning(msgBox,
                                          self.mainWindow.tr("Warning"),
                                          self.mainWindow.tr(message))
        return message

    def error(self, message, popUp=True, exc_info=True):
        self.linkScopeLogger.error(message, exc_info=exc_info)
        if popUp:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)
            QtWidgets.QMessageBox.critical(msgBox,
                                           self.mainWindow.tr("Error"),
                                           self.mainWindow.tr(message))
        return message

    def critical(self, message, popUp=True, exc_info=True):
        self.linkScopeLogger.critical(message, exc_info=exc_info)
        if popUp:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setStyleSheet(Stylesheets.MAIN_WINDOW_STYLESHEET)
            QtWidgets.QMessageBox.critical(msgBox,
                                           self.mainWindow.tr("Critical"),
                                           self.mainWindow.tr(message))
        return message

    # Set the severity level
    def setSeverityLevel(self, level: int):
        currentLogLevel = self.linkScopeLogger.level
        try:
            level = int(level)
            self.linkScopeLogger.setLevel(level)
            self.mainWindow.SETTINGS.setValue("Logging/Severity", self.linkScopeLogger.level)
        except ValueError:
            self.warning("Invalid Severity Level specified.")
            self.linkScopeLogger.setLevel(currentLogLevel)
            self.mainWindow.SETTINGS.setValue("Logging/Severity", currentLogLevel)

    def getSeverityLevel(self):
        return self.linkScopeLogger.level

    def changeLogfile(self, newLogFile):
        self.mainWindow.SETTINGS.setValue("Logging/Logfile", newLogFile)
        self.logFileHandler = logging.FileHandler(
            self.mainWindow.SETTINGS.value("Logging/Logfile", str(Path.home() / 'LinkScope_logfile.log')), 'a')
        for handler in self.linkScopeLogger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                self.linkScopeLogger.removeHandler(handler)
        self.linkScopeLogger.addHandler(self.logFileHandler)

    def __init__(self, parentObject):
        self.mainWindow = parentObject
        self.logQueue = Queue()
        self.logFileHandler = logging.FileHandler(
            self.mainWindow.SETTINGS.value("Logging/Logfile", str(Path.home() / 'LinkScope_logfile.log')), 'a')
        self.logQueueHandler = handlers.QueueHandler(self.logQueue)
        self.logFormatter = logging.Formatter(
            '{' + self.mainWindow.SETTINGS.value("Project/Name", "Untitled") + '} [%(asctime)s] - %(levelname)s: %('
                                                                               'message)s')
        self.logFormatterQueue = logging.Formatter('[%(asctime)s] - %(levelname)s: %(message)s')
        self.logFileHandler.setFormatter(self.logFormatter)
        self.logQueueHandler.setFormatter(self.logFormatterQueue)

        # Do not handle root logger messages
        rootLogger = logging.getLogger()
        for handler in rootLogger.handlers[:]:
            if isinstance(handler, logging.Handler):
                rootLogger.removeHandler(handler)

        self.linkScopeLogger = logging.getLogger('LinkScope_Logger')
        self.linkScopeLogger.addHandler(self.logFileHandler)
        self.linkScopeLogger.addHandler(self.logQueueHandler)

        self.setSeverityLevel(self.mainWindow.SETTINGS.value("Logging/Severity", logging.INFO))
