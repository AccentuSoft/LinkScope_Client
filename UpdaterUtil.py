#!/usr/bin/env python3
import sys
import time
from pathlib import Path

import py7zr


def main():
    if len(sys.argv) != 3:
        sys.exit(3)

    tempPath = Path(sys.argv[1])
    softwarePath = Path(sys.argv[2])

    time.sleep(10)  # Wait for a few seconds for the main application to close.

    input("\nPlease make sure that all LinkScope Client processes are closed, "
          "and then press Enter to begin the update.\n")
    print("Updating...\n")

    with py7zr.SevenZipFile(tempPath, 'r') as archive:
        archive.extractall(path=softwarePath.parent)

    tempPath.unlink(missing_ok=True)

    input("Update complete. Press Enter to exit.")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        input(f"Update failed. Press Enter to exit. Reason: {repr(e)}")
