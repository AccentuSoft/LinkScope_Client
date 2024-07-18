@ECHO OFF

:: NOTE: Need to compile versions of the magic library for windows from here: https://github.com/nscaife/file-windows.git
:: Then, put everything in the output folder (i.e. 'dist') in the magic folder.
:: Make sure that the libmagic dll actually has the name 'libmagic-1.dll'.

:: Copy the Resources, Core and magic directories, as well as Icon.ico, LinkScope.py, requirements.txt,
::   UpdaterUtil.py and PatchMagicWin.py to a new directory along with this file.
:: Then, run the script.

SET PYTHON_VER=3.11

python -m venv buildEnv

call buildEnv\Scripts\activate.bat

python -m pip install --upgrade wheel pip nuitka ordered-set

python -m pip cache purge

python -m pip install --upgrade -r requirements.txt

:: Patch magic library with our own binaries
python PatchMagicWin.py

python -m nuitka --follow-imports --standalone --noinclude-pytest-mode=nofollow --noinclude-setuptools-mode=nofollow ^
--noinclude-custom-mode=setuptools:error --noinclude-IPython-mode=nofollow --enable-plugin=pyside6 ^
--noinclude-unittest-mode=nofollow --assume-yes-for-downloads --remove-output --windows-console-mode=disable ^
--nofollow-import-to=tkinter ^
--include-data-dir="Resources=Resources" --include-package=Core ^
--include-data-dir="Core\Entities=Core\Entities" ^
--warn-unusual-code --show-modules --include-data-files="Icon.ico=Icon.ico" ^
--windows-icon-from-ico=".\Icon.ico" --include-data-dir="magic=magic" --windows-company-name=AccentuSoft ^
--windows-product-name="LinkScope Client" --windows-product-version="1.6.3.0" ^
--windows-file-description="LinkScope Client Software" ^
--include-package-data=playwright ^
--include-package-data=folium --include-package-data=branca ^
--include-package=dns ^
--include-package-data=pycountry ^
--include-package=jellyfish ^
--include-package=ipwhois ^
".\LinkScope.py"

python -m nuitka --onefile --noinclude-pytest-mode=nofollow ^
--noinclude-setuptools-mode=nofollow --noinclude-custom-mode=setuptools:error --noinclude-IPython-mode=nofollow ^
--noinclude-unittest-mode=nofollow --assume-yes-for-downloads --remove-output ^
--nofollow-import-to=tkinter ^
--warn-unusual-code ^
--windows-company-name=AccentuSoft --windows-product-version="1.6.3.0" ^
--windows-product-name="LinkScope Client Updater" --windows-file-description="LinkScope Client Updater" ^
".\UpdaterUtil.py"

:: We need the code, dll & etc files to be present.
xcopy Core\Resolutions LinkScope.dist\Core\Resolutions /S /E /Y
xcopy magic LinkScope.dist\magic /S /E /Y
move UpdaterUtil.exe LinkScope.dist\UpdaterUtil.exe
move LinkScope.dist LinkScope

call buildEnv\Scripts\deactivate.bat