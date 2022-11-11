#!/usr/bin/env python3

import zipfile
import magic
from pathlib import Path
from os import symlink
from shutil import copy2
from hashlib import sha3_512
from binascii import hexlify
from urllib.parse import urlparse

from PySide6 import QtCore


class URLManager:
    """
    This class handles URLs. If they are local, the appropriate entity
    is created to represent the type of file (Document, Image etc).

    The only archive type supported as of now is Zip.

    Note that there is no need to add entities to the database here, as
    they will be added by the class that is calling functionality from this one.
    """

    def __init__(self, mainWindow):
        self.mainWindow = mainWindow

    def handleURLs(self, urls):
        """
        Takes a list of QUrls and returns a list of entities that correspond
        to them.
        """
        return [self.handleURL(url) for url in urls]

    def handleURL(self, url):
        parsedURL = urlparse(url.toString())
        if not url.isValid() or (not all([parsedURL.scheme, parsedURL.netloc]) and parsedURL.scheme != 'file'):
            return None
        if url.isLocalFile():
            return self.handleLocalURL(url)
        else:
            return self.handleRemoteURL(url)

    def handleURLString(self, urlString):
        return self.handleURL(QtCore.QUrl(urlString))

    def handleLocalURL(self, url):
        urlPath = Path(url.toLocalFile())

        urlName = urlPath.name
        urlPathString = str(urlPath)
        savePathString = str(self.moveURLToProjectFilesHelperIfNeeded(urlPath))

        if savePathString == 'None':
            return None

        fileType = magic.from_file(urlPathString, mime=True)
        fileTypeSplit1, fileTypeSplit2 = fileType.split('/', 1)
        # CSV files not considered - may have any dialect, hard to accommodate.
        if urlPath.suffix in ('.ods', '.xls', '.xlsm', '.xlsx') and \
                fileTypeSplit2 in ('vnd.oasis.opendocument.spreadsheet',
                                   'vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                   'vnd.ms-excel',
                                   'vnd.openxmlformats-officedocument.spreadsheetml.sheet'):
            entityJson = {"Spreadsheet Name": urlName,
                          "File Path": savePathString,
                          "Entity Type": "Spreadsheet"}
        # Only support zip files for archives (for now) 10/Jul/2021).
        elif zipfile.is_zipfile(urlPathString):
            entityJson = {"Archive Name": urlName, "File Path": savePathString, "Entity Type": "Archive"}
        elif fileTypeSplit1 == "video":
            entityJson = {"Video Name": urlName, "File Path": savePathString, "Entity Type": "Video"}
        elif fileTypeSplit1 == "image":
            entityJson = {"Image Name": urlName, "File Path": savePathString, "Entity Type": "Image"}
        else:
            entityJson = {"Document Name": urlName, "File Path": savePathString, "Entity Type": "Document"}
        return entityJson

    def moveURLToProjectFilesHelperIfNeeded(self, urlPath: Path):
        valuePath = Path(urlPath).absolute()

        if not valuePath.exists() or not valuePath.is_file():
            return None

        projectFilesPath = Path(self.mainWindow.SETTINGS.value("Project/FilesDir")).absolute()
        try:
            savePath = valuePath.relative_to(projectFilesPath)
        except ValueError:
            # The file selected is not in Project Files
            createSymlink = self.mainWindow.SETTINGS.value("Project/Symlink or Copy Materials") == "Symlink"

            projectFilesPath = Path(self.mainWindow.SETTINGS.value("Project/FilesDir"))
            # Create a unique path in Project Files
            saveHash = hexlify(sha3_512(str(urlPath).encode()).digest()).decode()[:16]  # nosec
            savePath = projectFilesPath / f'{saveHash}|{urlPath.name}'

            if createSymlink:
                symlink(urlPath, savePath)
            else:
                copy2(urlPath, savePath)

            savePath = savePath.relative_to(projectFilesPath)

        return savePath

    def handleRemoteURL(self, url):
        stringURL = url.toString()
        return {'Entity Type': 'Onion Website', 'Onion URL': stringURL} \
            if self.mainWindow.RESOURCEHANDLER.runCheckOnAttribute(stringURL, 'Onion') \
            else {'Entity Type': 'Website', 'URL': stringURL}
