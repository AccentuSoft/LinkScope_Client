#!/bin/bash

# Copy the Modules, Resources and Core directories, as well as Icon.ico, LinkScope.py and requirements.txt to a new directory along with this file.
# Then, run the script.

PYTHON_VER=3.9

python${PYTHON_VER} -m venv buildEnv

source buildEnv/bin/activate

# orderedset package installed for compile time performance.
python${PYTHON_VER} -m pip install --upgrade wheel pip nuitka orderedset

python${PYTHON_VER} -m pip cache purge

python${PYTHON_VER} -m pip install -r requirements.txt

# Stop snscrape from messing with directories that will not exist in the final build.
echo "" > "buildEnv/lib/python${PYTHON_VER}/site-packages/snscrape/modules/__init__.py"

PLAYWRIGHT_BROWSERS_PATH=0 python${PYTHON_VER} -m playwright install

FIREFOX_VER=$(python -c "from pathlib import Path;x=Path(\"buildEnv/lib/python${PYTHON_VER}/site-packages/playwright/driver/package/.local-browsers\");print(list(x.glob(\"firefox*/firefox\"))[0].parent.name.split(\"-\")[1])")

python${PYTHON_VER} -m nuitka --follow-imports --standalone --noinclude-pytest-mode=nofollow \
--noinclude-setuptools-mode=nofollow --noinclude-custom-mode=setuptools:error --noinclude-IPython-mode=nofollow \
--enable-plugin=pyside6 --enable-plugin=numpy --enable-plugin=trio --assume-yes-for-downloads --remove-output \
--disable-console --include-data-dir="Resources=Resources" --include-plugin-directory=Modules --include-package=Core \
--include-data-dir="Core/Entities=Core/Entities" --include-data-dir="Core/Resolutions/Core=Core/Resolutions/Core" \
--include-data-dir="Modules=Modules" --warn-unusual-code --show-modules --include-data-files="Icon.ico=Icon.ico" \
--linux-icon="Icon.ico" \
--include-package-data=playwright \
--include-package-data=folium --include-package-data=branca \
--include-package=social-analyzer --include-package-data=langdetect --include-package-data=tld \
--include-package=Wappalyzer --include-package-data=Wappalyzer \
--include-package=dns \
--include-package=holehe.modules \
--include-package=snscrape \
--include-package=docker --include-package-data=docker \
--include-package-data=pycountry \
--include-package=jellyfish \
--include-package=ipwhois \
--include-package=tweepy \
--include-data-dir="buildEnv/lib/python${PYTHON_VER}/site-packages/playwright/driver/package/.local-browsers/firefox-${FIREFOX_VER}/firefox=playwright/driver/package/.local-browsers/firefox-${FIREFOX_VER}/firefox" \
LinkScope.py

deactivate
