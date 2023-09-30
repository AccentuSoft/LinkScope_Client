#!/usr/bin/env python3

import contextlib
import platform
import subprocess
import requests
import tempfile
import shutil
import os
import ctypes

from pathlib import Path
from semver import compare
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
                and compare(self.mainWindow.SETTINGS.value("Program/Version").lstrip('v'),
                            latest_version.lstrip('v')) < 0
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

    def finalizeUpdate(self, updateTempPath: str) -> None:
        if updateTempPath != '':
            latest_version = self.getLatestVersion()
            self.mainWindow.SETTINGS.setValue("Program/Version", latest_version)
            self.mainWindow.MESSAGEHANDLER.info('Updating done, please restart for the changes to take effect.')
            self.mainWindow.MESSAGEHANDLER.info("The application will now save and close to apply the updates. "
                                                "Please wait for a few minutes before reopening LinkScope.",
                                                popUp=True)

            uncompressNewVersion(
                self.system,
                self.mainWindow.SETTINGS.value("Program/BaseDir"),
                str(self.baseSoftwarePath),
                updateTempPath)
            self.mainWindow.close()

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
    updateDoneSignal = QtCore.Signal(str)

    def __init__(self, updateManager, mainWindow):
        super().__init__()
        self.mainWindow = mainWindow
        self.updateManager = updateManager

    def run(self) -> None:
        try:
            downloadUrl = self.updateManager.getDownloadURL()
            clientTempCompressedArchive = tempfile.mkstemp(suffix='.7z')
            tempPath = clientTempCompressedArchive[1]

            with os.fdopen(clientTempCompressedArchive[0], 'wb') as tempArchive:
                with requests.get(downloadUrl, stream=True) as fileStream:
                    for chunk in fileStream.iter_content(chunk_size=5 * 1024 * 1024):
                        tempArchive.write(chunk)
            self.updateDoneSignal.emit(tempPath)
        except Exception:
            self.updateDoneSignal.emit('')


def uncompressNewVersion(system: str, baseDir: str, baseSoftwarePath: str, updateTempPath: str):
    tempDir = tempfile.mkdtemp(prefix='LinkScope_Updater_TMP_')

    if system == 'Windows':
        updaterPath = Path(baseDir) / "UpdaterUtil.exe"

        tempUpdaterPath = Path(tempDir) / updaterPath.name
        shutil.copy(updaterPath, tempUpdaterPath)

        # This is done so that Windows spawns the updater as a detached process.
        ShellExecuteEx = ctypes.windll.shell32.ShellExecuteEx
        SEE_MASK_NO_CONSOLE = 0x00008000

        class SHELLEXECUTEINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_ulong),
                ("fMask", ctypes.c_ulong),
                ("hwnd", ctypes.c_void_p),
                ("lpVerb", ctypes.c_char_p),
                ("lpFile", ctypes.c_char_p),
                ("lpParameters", ctypes.c_char_p),
                ("lpDirectory", ctypes.c_char_p),
                ("nShow", ctypes.c_int),
                ("hInstApp", ctypes.c_void_p),
                ("lpIDList", ctypes.c_void_p),
                ("lpClass", ctypes.c_char_p),
                ("hkeyClass", ctypes.c_void_p),
                ("dwHotKey", ctypes.c_ulong),
                ("hIconOrMonitor", ctypes.c_void_p),
                ("hProcess", ctypes.c_void_p),
            ]

        sei = SHELLEXECUTEINFO()
        sei.cbSize = ctypes.sizeof(sei)
        sei.fMask = SEE_MASK_NO_CONSOLE
        sei.lpVerb = b"runas"
        sei.lpFile = bytes(tempUpdaterPath)
        sei.lpParameters = f'"{updateTempPath}" "{baseSoftwarePath}"'.encode('utf-8')
        sei.nShow = 1

        if not ShellExecuteEx(ctypes.byref(sei)):
            raise ctypes.WinError()

    elif system == 'Linux':
        updaterPath = Path(baseDir) / "UpdaterUtil"

        tempUpdaterPath = Path(tempDir) / updaterPath.name
        shutil.copy(updaterPath, tempUpdaterPath)

        subprocess.Popen(
            f'pkexec "{tempUpdaterPath}" "{updateTempPath}" "{baseSoftwarePath}"',
            start_new_session=True,
            close_fds=True,
            shell=True,
        )
