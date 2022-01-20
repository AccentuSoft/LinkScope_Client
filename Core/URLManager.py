#!/usr/bin/env python3

import zipfile
import magic
from pathlib import Path
from os import symlink
from shutil import copy2
from hashlib import sha3_512
from binascii import hexlify

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
        if len(urls) == 1:
            url = urls[0]
            entityJson = self.handleURL(url)
            return [entityJson]

        returnValue = []
        for url in urls:
            returnValue += [self.handleURL(url)]

        return returnValue

    def handleURL(self, url):
        if not url.isValid():
            return None
        if url.isLocalFile():
            return self.handleLocalURL(url)
        else:
            return self.handleRemoteURL(url)

    def handleURLString(self, urlString):
        self.handleURL(QtCore.QUrl(urlString))

    def handleLocalURL(self, url):
        urlPath = Path(url.toLocalFile())

        urlName = urlPath.name
        urlPathString = str(urlPath)
        savePathString = str(self.moveURLToProjectFilesHelperIfNeeded(urlPath))

        if savePathString == 'None':
            return None

        # Only support zip files for archives (for now) 10/Jul/2021).
        if zipfile.is_zipfile(urlPathString):
            entityJson = {"Archive Name": urlName, "File Path": savePathString, "Entity Type": "Archive"}
        else:
            fileType = magic.from_file(urlPathString, mime=True).split('/')[0]
            if fileType == "video":
                entityJson = {"Video Name": urlName, "File Path": savePathString, "Entity Type": "Video"}
                pass
            elif fileType == "image":
                entityJson = {"Image Name": urlName, "File Path": savePathString, "Entity Type": "Image"}
                pass
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
            createSymlink = True if self.mainWindow.SETTINGS.value("Project/Symlink or Copy Materials") == "Symlink" \
                else False
            projectFilesPath = Path(self.mainWindow.SETTINGS.value("Project/FilesDir"))
            # Create a unique path in Project Files
            saveHash = hexlify(sha3_512(str(urlPath).encode()).digest()).decode()[:16]  # nosec
            savePath = projectFilesPath / (saveHash + '|' + urlPath.name)

            if createSymlink:
                symlink(urlPath, savePath)
            else:
                copy2(urlPath, savePath)

            savePath = savePath.relative_to(projectFilesPath)

        return savePath

    def handleRemoteURL(self, url):
        entity = {'Entity Type': 'Website', 'URL': url.toString()}
        return entity
