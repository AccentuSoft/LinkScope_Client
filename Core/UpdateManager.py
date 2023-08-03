#!/usr/bin/env python3

import platform
import tempfile
import requests
import os
import py7zr

from pathlib import Path


class UpdateManager:

    def __init__(self, mainWindow):
        self.mainWindow = mainWindow
        self.system = platform.system()
        if self.system == 'Windows':
            self.baseSoftwarePath = Path(os.path.abspath(os.sep)) / 'Program Files' / 'LinkScope'
        else:
            self.baseSoftwarePath = Path(os.path.abspath(os.sep)) / 'usr' / 'local' / 'sbin' / 'LinkScope'

    def get_download_url(self):
        downloadURLBase = self.mainWindow.SETTINGS.value("Program/Update Source")
        if self.system == 'Windows':
            return f"{downloadURLBase}LinkScope-Windows-x64.7z"
        else:
            return f"{downloadURLBase}LinkScope-Ubuntu-x64.7z"

    def get_latest_version(self):
        version_req = requests.get(self.mainWindow.SETTINGS.value("Program/Version Check Source"),
                                   headers={'User-Agent': 'LinkScope Update Checker'})
        if version_req.status_code != 200:
            return None
        return version_req.json()['tag_name']

    def is_update_available(self):
        latest_version = self.get_latest_version()
        return (
            latest_version is not None
            and self.mainWindow.SETTINGS.value("Program/Version") < latest_version
        )

    def do_update(self):
        downloadUrl = self.get_download_url()
        clientTempCompressedArchive = tempfile.mkstemp(suffix='.7z')
        tempPath = Path(clientTempCompressedArchive[1])

        with os.fdopen(clientTempCompressedArchive[0], 'wb') as tempArchive:
            with requests.get(downloadUrl, stream=True) as fileStream:
                for chunk in fileStream.iter_content(chunk_size=5 * 1024 * 1024):
                    tempArchive.write(chunk)

        with py7zr.SevenZipFile(tempPath, 'r') as archive:
            archive.extractall(path=self.baseSoftwarePath.parent)

        tempPath.unlink(missing_ok=True)