@ECHO OFF

:: NOTE: Need to compile versions of the magic library for windows from here: https://github.com/nscaife/file-windows.git
:: Then, put everything in the output folder (i.e. 'dist') in the magic folder.
:: Make sure that the libmagic dll actually has the name 'libmagic-1.dll'.

:: Copy the Modules, Resources, Core and magic directories, as well as Icon.ico, LinkScope.py, requirements.txt,
::   PatchMagicWin.py to a new directory along with this file.
:: Then, run the script.

SET PYTHON_VER=3.9

python -m venv buildEnv

call buildEnv\Scripts\activate.bat

python -m pip install --upgrade wheel pip nuitka orderedset

python -m pip cache purge

python -m pip install -r requirements.txt

:: Patch magic library with our own binaries
python PatchMagicWin.py

:: Stop snscrape from messing with directories that will not exist in the final build.
echo "" > "buildEnv\Lib\site-packages\snscrape\modules\__init__.py"

SET PLAYWRIGHT_BROWSERS_PATH=0
playwright install

FOR /F "usebackq" %%L in (`python -c "from pathlib import Path;x=Path('buildEnv\Lib\site-packages\playwright\driver\package\.local-browsers');print(list(x.glob('firefox*/firefox'))[0].parent.name.split('-')[1])"`) DO SET FIREFOX_VER=%%L


python -m nuitka --follow-imports --standalone --noinclude-pytest-mode=nofollow --noinclude-setuptools-mode=nofollow ^
--noinclude-custom-mode=setuptools:error --noinclude-IPython-mode=nofollow --enable-plugin=pyside6 ^
--enable-plugin=numpy --enable-plugin=trio --assume-yes-for-downloads --remove-output --disable-console ^
--include-data-dir="Resources=Resources" --include-plugin-directory=Modules --include-package=Core ^
--include-data-dir="Core\Entities=Core\Entities" --include-data-dir="Core\Resolutions\Core=Core\Resolutions\Core" ^
--include-data-dir="Modules=Modules" --warn-unusual-code --show-modules --include-data-files="Icon.ico=Icon.ico" ^
--windows-icon-from-ico=".\Icon.ico" --include-data-dir="magic=magic" --windows-company-name=AccentuSoft ^
--windows-product-name="LinkScope Client" --windows-product-version="1.3.8.0" ^
--windows-file-description="LinkScope Client Software" ^
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
".\LinkScope.py"

call buildEnv\Scripts\deactivate.bat