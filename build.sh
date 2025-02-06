#!/bin/bash

# Copy the Resources and Core directories, as well as Icon.ico, LinkScope.py, UpdaterUtil.py and requirements.txt
#   to a new directory along with this file.
# Then, run the script.

PYTHON_VER=3.13

python${PYTHON_VER} -m venv buildEnv

source buildEnv/bin/activate

# orderedset package installed for compile time performance.
python${PYTHON_VER} -m pip install --upgrade wheel pip nuitka ordered-set

python${PYTHON_VER} -m pip cache purge

python${PYTHON_VER} -m pip install --upgrade -r requirements.txt

python${PYTHON_VER} -m nuitka --follow-imports --standalone --noinclude-pytest-mode=nofollow \
--noinclude-setuptools-mode=nofollow --noinclude-custom-mode=setuptools:error --noinclude-IPython-mode=nofollow \
--noinclude-unittest-mode=nofollow --enable-plugin=pyside6 --assume-yes-for-downloads --remove-output \
--nofollow-import-to=tkinter \
--include-data-dir="Resources=Resources" --include-package=Core \
--include-data-dir="Core/Entities=Core/Entities" \
--warn-unusual-code --show-modules --include-data-files="Icon.ico=Icon.ico" \
--linux-icon="Icon.ico" \
--include-package-data=requests \
--include-package-data=folium --include-package-data=branca \
--include-package=dns \
--include-package-data=pycountry \
--include-package=jellyfish \
--include-package=ipwhois \
LinkScope.py

python${PYTHON_VER} -m nuitka --onefile --noinclude-pytest-mode=nofollow \
--noinclude-setuptools-mode=nofollow --noinclude-custom-mode=setuptools:error --noinclude-IPython-mode=nofollow \
--noinclude-unittest-mode=nofollow --assume-yes-for-downloads --remove-output \
--nofollow-import-to=tkinter \
--warn-unusual-code \
UpdaterUtil.py

# We need the code, dll & etc files to be present.
cp -r Core/Resolutions LinkScope.dist/Core
mv UpdaterUtil.bin LinkScope.dist/UpdaterUtil

mv LinkScope.dist/ LinkScope
mv LinkScope/LinkScope.bin LinkScope/LinkScope

deactivate
