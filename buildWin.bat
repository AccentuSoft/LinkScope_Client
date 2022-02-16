@ECHO OFF

:: Copy the Modules, Resources and Core directories, as well as Icon.ico, LinkScope.py and requirements.txt to a new directory along with this file.
:: Then, run the script.

python -m venv buildEnv

call buildEnv\Scripts\activate.bat

python -m pip install --upgrade pip pyinstaller

python -m pip install --upgrade -r requirements.txt

set PLAYWRIGHT_BROWSERS_PATH=0
playwright install

:: Just in case this was not uncommented in the requirements.txt file.
python -m pip install --upgrade python-magic-bin

python -m PyInstaller --clean --icon="Icon.ico" --noconsole --noconfirm --onedir --add-data "Modules;Modules" --add-data "Resources;Resources" --add-data "Core;Core" --collect-all "PySide6" --collect-all "networkx" --collect-all "pydot" --collect-all "msgpack" --hidden-import "_cffi_backend" --collect-all "folium" --collect-all "shodan" --collect-all "vtapi3" --collect-all "docker" --collect-all "exif" --collect-all "dns" --collect-all "pycountry" --collect-all "tldextract" --collect-all "requests_futures" --collect-all "branca" --collect-all "bs4" --hidden-import "pandas" --collect-all "docx2python" --collect-all "tweepy" --collect-all "PyPDF2" --collect-all "Wappalyzer" --collect-all "email_validator" --add-data "C:\Users\IEUser\AppData\Roaming\Python\Python39\site-packages\social-analyzer;social-analyzer" --hidden-import "PIL" --hidden-import "lz4" --hidden-import "lxml" --hidden-import "jellyfish" --hidden-import "logging" --hidden-import "defusedxml" --hidden-import "dateutil" --hidden-import "xmltodict" --hidden-import "urllib3" --hidden-import "cchardet" --hidden-import "ipwhois" --hidden-import "holehe" --hidden-import "httpx" --collect-all "snscrape" --hidden-import "pytz" --hidden-import "python-magic-bin" ".\LinkScope.py"

:: Copy web engine resources in final package, so that the map tool works.
xcopy buildEnv\Lib\site-packages\PySide6\resources\qtwebengine_resources.pak dist\LinkScope /Y
xcopy buildEnv\Lib\site-packages\PySide6\resources\qtwebengine_devtools_resources.pak dist\LinkScope /Y
xcopy buildEnv\Lib\site-packages\PySide6\resources\qtwebengine_resources_100p.pak dist\LinkScope /Y
xcopy buildEnv\Lib\site-packages\PySide6\resources\qtwebengine_resources_200p.pak dist\LinkScope /Y
xcopy buildEnv\Lib\site-packages\PySide6\resources\icudtl.dat dist\LinkScope /Y
:: Copy web libraries to a location that can be found by the system automatically.
:: Can't do globbing on cmd shell. Will need to update this later on.
xcopy dist\LinkScope\site-packages\playwright\driver\package\.local-browsers\firefox-1316\firefox\* dist\LinkScope /S /Y
xcopy dist\LinkScope\site-packages\playwright\driver\package\.local-browsers\firefox-1316\firefox\* dist\LinkScope\playwright\driver\package\.local-browsers\firefox-1316\firefox /S /Y
xcopy Icon.ico dist\LinkScope /Y

call buildEnv\Scripts\deactivate.bat