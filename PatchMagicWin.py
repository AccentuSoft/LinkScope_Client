# This file patches the magic library on Windows so that it works properly after being compiled.

import re
from pathlib import Path

magicLibPath = Path.cwd() / "buildEnv" / "Lib" / "site-packages" / "magic" / "loader.py"

with open(magicLibPath, 'r') as magicLibFile:
    magicLines = magicLibFile.readlines()

# Find out what level of indentation is used, in case it changes in the future.
lineIndent = None
for line in magicLines:
    if line.startswith(' '):
        lineIndent = len(re.split(r'\S', line)[0])
        break

magicLines.insert(0, 'from pathlib import Path\n')

funcIndex = magicLines.index('def _lib_candidates():\n')

# This patch is only done on Windows, so we can safely 'hardcode' the path to the dll, since we're the ones
#   providing it.
magicLines.insert(funcIndex + 1, ' ' * lineIndent + 'yield str(Path(__file__).parent / "libmagic-1.dll")\n')

with open(magicLibPath, 'w') as magicLibFile:
    magicLibFile.writelines(magicLines)
