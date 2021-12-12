@ECHO OFF

:: Copy the Modules, Resources and Core directories, as well as Icon.ico, Nexus.py and requirements.txt to a new directory along with this file.
:: Then, run the script.

python -m venv buildEnv

call buildEnv\Scripts\activate.bat

python -m pip install --upgrade pip pyinstaller

python -m pip install --upgrade -r requirements.txt

:: Just in case this was not uncommented in the requirements.txt file.
python -m pip install --upgrade python-magic-bin

python -m PyInstaller --clean --icon="Icon.ico" --noconsole --noconfirm --onedir --windowed --add-data "Modules;Modules" --add-data "Resources;Resources" --add-data "Core;Core" --collect-all "PySide6" --collect-all "networkx" --collect-all "pydot" --collect-all "msgpack" --hidden-import "_cffi_backend" --collect-all "folium" --collect-all "shodan" --collect-all "vtapi3" --collect-all "docker" --collect-all "exif" --collect-all "dns" --collect-all "pycountry" --collect-all "tldextract" --collect-all "requests_futures" --collect-all "branca" --collect-all "bs4" --hidden-import "pandas" --collect-all "docx2python" --collect-all "tweepy" --collect-all "PyPDF2" --collect-all "Wappalyzer" --collect-all "email_validator" --collect-all "seleniumwire" --add-data "C:\Users\IEUser\AppData\Roaming\Python\Python39\site-packages\social-analyzer;social-analyzer" --hidden-import "PIL" --hidden-import "lz4" --hidden-import "lxml" --hidden-import "jellyfish" --hidden-import "logging" --hidden-import "python-magic-bin" ".\Nexus.py"

:: Copy web engine resources in final package, so that the map tool works.
copy buildEnv\Lib\site-packages\PySide6\resources\qtwebengine_resources.pak dist\Nexus
copy buildEnv\Lib\site-packages\PySide6\resources\qtwebengine_devtools_resources.pak dist\Nexus
copy buildEnv\Lib\site-packages\PySide6\resources\qtwebengine_resources_100p.pak dist\Nexus
copy buildEnv\Lib\site-packages\PySide6\resources\qtwebengine_resources_200p.pak dist\Nexus
copy buildEnv\Lib\site-packages\PySide6\resources\icudtl.dat dist\Nexus

call buildEnv\Scripts\deactivate.bat