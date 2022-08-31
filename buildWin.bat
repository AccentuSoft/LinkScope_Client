@ECHO OFF

:: Copy the Modules, Resources and Core directories, as well as Icon.ico, LinkScope.py and requirements.txt to a new directory along with this file.
:: Then, run the script.

SET /A PYTHON_VER = 3.9

python -m venv buildEnv

call buildEnv\Scripts\activate.bat

python -m pip install --upgrade wheel pip nuitka orderedset

python -m pip cache purge

python -m pip install -r requirements.txt

:: Stop snscrape from messing with directories that will not exist in the final build.
echo "" > "buildEnv\Lib\site-packages\snscrape\modules\__init__.py"

set PLAYWRIGHT_BROWSERS_PATH=0
playwright install

SET /A FIREFOX_VER = (`python -c 'from pathlib import Path;x=Path("buildEnv\Lib\site-packages\playwright\driver\package\.local-browsers");print(list(x.glob("firefox*\firefox"))[0].parent.name.split("-")[1])'`)

:: Just in case this was not uncommented in the requirements.txt file.
python -m pip install --upgrade python-magic-bin

python -m nuitka --follow-imports --standalone --noinclude-pytest-mode=nofollow --noinclude-setuptools-mode=nofollow ^
--noinclude-custom-mode=setuptools:error --noinclude-IPython-mode=nofollow --enable-plugin=pyside6 ^
--enable-plugin=numpy --enable-plugin=trio --assume-yes-for-downloads --remove-output --disable-console ^
--include-data-dir="Resources=Resources" --include-plugin-directory=Modules --include-plugin-directory=Core ^
--warn-unusual-code --show-modules --include-data-files="Icon.ico=Icon.ico" --windows-icon-from-ico="Icon.ico" ^
--windows-company-name=AccentuSoft --windows-product-name=LinkScope --windows-product-version="1.3.8.0" --onefile-tempdir-spec='%TEMP%\LinkScope_%PID%_%TIME%' ^
--include-package-data=playwright ^
--include-package-data=folium --include-package-data=branca ^
--include-package=social-analyzer --include-package-data=langdetect --include-package-data=tld ^
--include-package=Wappalyzer --include-package-data=Wappalyzer ^
--include-package=dns ^
--include-package=holehe.modules ^
--include-package=snscrape ^
--include-package=docker --include-package-data=docker ^
--include-package-data=pycountry ^
--include-package=jellyfish ^
--include-package=ipwhois ^
--include-package=tweepy ^
--include-data-dir="buildEnv\Lib\site-packages\playwright\driver\package\.local-browsers\firefox-%FIREFOX_VER%\firefox=playwright\driver\package\.local-browsers\firefox-%FIREFOX_VER%\firefox" ^
--include-package "python-magic-bin" ".\LinkScope.py"

call buildEnv\Scripts\deactivate.bat