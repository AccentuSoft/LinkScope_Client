#!/usr/bin/env python3

import sys
import tempfile
import os
import requests
import py7zr
from pathlib import Path

if len(sys.argv) != 3:
    sys.exit(3)

downloadUrl = sys.argv[1]
softwarePath = sys.argv[2]

clientTempCompressedArchive = tempfile.mkstemp(suffix='.7z')
tempPath = Path(clientTempCompressedArchive[1])

with os.fdopen(clientTempCompressedArchive[0], 'wb') as tempArchive:
    with requests.get(downloadUrl, stream=True) as fileStream:
        for chunk in fileStream.iter_content(chunk_size=5 * 1024 * 1024):
            tempArchive.write(chunk)

with py7zr.SevenZipFile(tempPath, 'r') as archive:
    archive.extractall(path=softwarePath)

tempPath.unlink(missing_ok=True)
