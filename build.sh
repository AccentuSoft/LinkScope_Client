#!/bin/bash

# Copy the Modules, Resources and Core directories, as well as Icon.ico, LinkScope.py and requirements.txt to a new directory along with this file.
# Then, run the script.

python3.9 -m venv buildEnv

source buildEnv/bin/activate

python3.9 -m pip install --upgrade wheel pip pyinstaller

python3.9 -m pip cache purge

python3.9 -m pip install -r requirements.txt

PLAYWRIGHT_BROWSERS_PATH=0 python3.9 -m playwright install

# Numpy cannot be loaded without the 'noarchive' debug flag - bug?
python3.9 -m PyInstaller --clean --icon="./Icon.ico" --noconsole --noconfirm --onedir --noupx -d noarchive \
--add-data "./Modules:Modules/" --add-data "./Resources:Resources/" --add-data "./Core:Core/" \
--collect-all "PySide6" --collect-all "networkx" --collect-all "pydot" --collect-all "msgpack" \
--hidden-import "_cffi_backend" --collect-all "folium" --collect-all "shodan" --collect-all "vtapi3" \
--collect-all "docker" --collect-all "exif" --collect-all "pycountry" --collect-all "tldextract" \
--collect-all "requests_futures" --collect-all "branca" --collect-all "bs4" --hidden-import "pandas" \
--collect-all "docx2python" --collect-all "tweepy" --collect-all "PyPDF2" --collect-all "Wappalyzer" \
--collect-all "email_validator" --collect-all "social-analyzer" --collect-all "tld" \
--hidden-import "PIL" --hidden-import "lz4" --hidden-import "lxml" --hidden-import "jellyfish" \
--hidden-import "defusedxml" --hidden-import "cchardet" --hidden-import "ipwhois" --hidden-import "xmltodict" \
--hidden-import "dateutil" --hidden-import "urllib3" --hidden-import "logging" --hidden-import "holehe" \
--hidden-import "httpx" --collect-all "snscrape" --hidden-import "pytz" --hidden-import "name-that-hash" \
"./LinkScope.py"

# Copy web engine resources in final package, so that the map tool works.
cp buildEnv/lib/python3.9/site-packages/PySide6/Qt/resources/qtwebengine_resources.pak dist/LinkScope
cp buildEnv/lib/python3.9/site-packages/PySide6/Qt/resources/qtwebengine_devtools_resources.pak dist/LinkScope
cp buildEnv/lib/python3.9/site-packages/PySide6/Qt/resources/qtwebengine_resources_100p.pak dist/LinkScope
cp buildEnv/lib/python3.9/site-packages/PySide6/Qt/resources/qtwebengine_resources_200p.pak dist/LinkScope
cp buildEnv/lib/python3.9/site-packages/PySide6/Qt/resources/icudtl.dat dist/LinkScope
# Copy web libraries to a location that can be found by the system automatically.
cp -r buildEnv/lib/python3.9/site-packages/playwright/driver/package/.local-browsers/firefox-*/firefox/* dist/LinkScope
cp -r buildEnv/lib/python3.9/site-packages/playwright/driver/package/.local-browsers/firefox-*/firefox/* dist/LinkScope/playwright/driver/package/.local-browsers/firefox-*/firefox
# Include the Icon.
cp Icon.ico dist/LinkScope

deactivate
