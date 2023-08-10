#!/usr/bin/env python3

import contextlib
import platform
import subprocess
import requests
import os

from pathlib import Path
from PySide6 import QtCore, QtWidgets


class UpdateManager:

    def __init__(self, mainWindow):
        self.updateThread = None
        self.mainWindow = mainWindow
        self.system = platform.system()
        if self.system == 'Windows':
            self.baseSoftwarePath = Path(os.path.abspath(os.sep)) / 'Program Files' / 'LinkScope'
        else:
            self.baseSoftwarePath = Path(os.path.abspath(os.sep)) / 'usr' / 'local' / 'sbin' / 'LinkScope'

    def getDownloadURL(self):
        downloadURLBase = self.mainWindow.SETTINGS.value("Program/Update Source")
        if self.system == 'Windows':
            return f"{downloadURLBase}LinkScope-Windows-x64.7z"
        else:
            return f"{downloadURLBase}LinkScope-Ubuntu-x64.7z"

    def getLatestVersion(self):
        with contextlib.suppress(Exception):
            version_req = requests.get(self.mainWindow.SETTINGS.value("Program/Version Check Source"),
                                       headers={'User-Agent': 'LinkScope Update Checker'})
            if version_req.status_code == 200:
                return version_req.json()['tag_name']
        return None

    def isUpdateAvailable(self):
        latest_version = self.getLatestVersion()
        return (
            latest_version is not None
            and self.mainWindow.SETTINGS.value("Program/Version") < latest_version
        )

    def doUpdate(self) -> None:
        if self.updateThread is not None:
            self.mainWindow.MESSAGEHANDLER.error('Update already in progress.')
            return
        self.mainWindow.MESSAGEHANDLER.info('Starting update...')
        self.updateThread = UpdaterThread(self, self.mainWindow)
        self.updateThread.updateDoneSignal.connect(self.finalizeUpdate)
        self.updateThread.start()
        self.mainWindow.MESSAGEHANDLER.info('Update in progress')

    def finalizeUpdate(self, success: bool) -> None:
        if success:
            latest_version = self.getLatestVersion()
            self.mainWindow.SETTINGS.setValue("Program/Version", latest_version)
            self.mainWindow.MESSAGEHANDLER.info('Updating done, please restart for the changes to take effect.')
        else:
            self.mainWindow.MESSAGEHANDLER.info('Updating failed.')


class UpdaterWindow(QtWidgets.QDialog):

    def __init__(self, mainWindow, updateManager: UpdateManager, updateAvailableOverride: bool = False):
        super().__init__()
        self.mainWindow = mainWindow
        self.updateManager = updateManager

        self.setWindowTitle('Update Manager')

        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)

        doUpdateButton = QtWidgets.QPushButton('Update')
        doUpdateButton.clicked.connect(self.initiateUpdate)
        cancelButton = QtWidgets.QPushButton('Close')
        cancelButton.clicked.connect(self.reject)

        updateAvailableLabel = QtWidgets.QLabel()
        updateAvailableLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        if updateAvailableOverride or updateManager.isUpdateAvailable():
            updateAvailableLabel.setText('An update for LinkScope is available.')
        else:
            updateAvailableLabel.setText('LinkScope is up to date.')
            doUpdateButton.setDisabled(True)
            doUpdateButton.setEnabled(False)

        layout.addWidget(updateAvailableLabel, 1, 1, 1, 2)
        layout.addWidget(cancelButton, 2, 1)
        layout.addWidget(doUpdateButton, 2, 2)

    def initiateUpdate(self) -> None:
        self.updateManager.doUpdate()
        self.accept()


class UpdaterThread(QtCore.QThread):
    updateDoneSignal = QtCore.Signal(bool)

    def __init__(self, updateManager, mainWindow):
        super().__init__()
        self.mainWindow = mainWindow
        self.updateManager = updateManager

    def run(self) -> None:
        downloadUrl = self.updateManager.getDownloadURL()
        if self.updateManager.system == 'Windows':
            subprocess.run(
                ['runas',
                 '/user:Administrator',
                 Path(self.mainWindow.SETTINGS.value("Program/BaseDir")) / "UpdaterUtil.exe",
                 downloadUrl,
                 self.updateManager.baseSoftwarePath.parent]
            )
        elif self.updateManager.system == 'Linux':
            subprocess.run(
                ['pkexec',
                 Path(self.mainWindow.SETTINGS.value("Program/BaseDir")) / "UpdaterUtil",
                 downloadUrl,
                 self.updateManager.baseSoftwarePath.parent]
            )
