#!/usr/bin/env python3

import logging

from pathlib import Path
from PySide6 import QtWidgets


class MessageHandler:
    """
    Class that handles logging.
    Requires a parent object which implements a 'getSettings' function
      that returns a Settings object.
    Call 'debug', 'info', 'warning', 'error' or 'critical' depending
      on severity.
    """

    def debug(self, message, exc_info=True):
        logging.debug(message, exc_info=exc_info)
        return message

    def info(self, message, popUp=False, exc_info=False):
        logging.info(message, exc_info=exc_info)
        if popUp:
            msgBox = QtWidgets.QMessageBox()
            QtWidgets.QMessageBox.information(msgBox,
                                              self.mainWindow.tr("Info"),
                                              self.mainWindow.tr(message))
        return message

    def warning(self, message, popUp=False, exc_info=False):
        logging.warning(message, exc_info=exc_info)
        if popUp:
            msgBox = QtWidgets.QMessageBox()
            QtWidgets.QMessageBox.warning(msgBox,
                                          self.mainWindow.tr("Warning"),
                                          self.mainWindow.tr(message))
        return message

    def error(self, message, popUp=True, exc_info=True):
        logging.error(message, exc_info=exc_info)
        if popUp:
            msgBox = QtWidgets.QMessageBox()
            QtWidgets.QMessageBox.critical(msgBox,
                                           self.mainWindow.tr("Error"),
                                           self.mainWindow.tr(message))
        return message

    def critical(self, message, popUp=True, exc_info=True):
        logging.critical(message, exc_info=exc_info)
        if popUp:
            msgBox = QtWidgets.QMessageBox()
            QtWidgets.QMessageBox.critical(msgBox,
                                           self.mainWindow.tr("Critical"),
                                           self.mainWindow.tr(message))
        return message

    # Set the severity level
    def setSeverityLevel(self, level):
        currentLogLevel = logging.root.level
        try:
            level = int(level)
            logging.root.setLevel(level)
            self.mainWindow.SETTINGS.setValue("Logging/Severity", logging.root.level)
        except ValueError:
            self.warning("Invalid Severity Level specified.")
            logging.root.setLevel(currentLogLevel)
            self.mainWindow.SETTINGS.setValue("Logging/Severity", currentLogLevel)

    def getSeverityLevel(self):
        return logging.root.level

    def changeLogfile(self, newLogFile):
        self.mainWindow.SETTINGS.setValue("Logging/Logfile", newLogFile)
        self.logFileHandler = logging.FileHandler(
            self.mainWindow.SETTINGS.value("Logging/Logfile", str(Path.home() / 'LinkScope_logfile.log')), 'a')
        rootLogger = logging.getLogger()
        for handler in rootLogger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                rootLogger.removeHandler(handler)
        rootLogger.addHandler(self.logFileHandler)

    def __init__(self, parentObject):
        self.mainWindow = parentObject
        self.logFileHandler = logging.FileHandler(
            self.mainWindow.SETTINGS.value("Logging/Logfile", str(Path.home() / 'LinkScope_logfile.log')), 'a')
        self.logFormatter = logging.Formatter(
            '{' + self.mainWindow.SETTINGS.value("Project/Name", "Untitled") + '} [%(asctime)s] - %(levelname)s: %('
                                                                               'message)s')
        self.logFileHandler.setFormatter(self.logFormatter)
        rootLogger = logging.getLogger()
        for handler in rootLogger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                rootLogger.removeHandler(handler)
        rootLogger.addHandler(self.logFileHandler)

        self.setSeverityLevel(self.mainWindow.SETTINGS.value("Logging/Severity", logging.INFO))
