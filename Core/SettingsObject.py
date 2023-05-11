#!/usr/bin/env python3

from msgpack import dump
from shutil import move
from pathlib import Path
from Core.PathHelper import is_path_exists_or_creatable_portable
from PySide6.QtCore import QSettings


class SettingsObject(dict):
    """
    Stores the following session settings:

    Project/Name: Self explanatory.
    Project/BaseDir: The directory in which the current project is stored.
    Program/BaseDir: The directory in which the program is stored.
    MainWindow/Geometry: Stores the window size
    MainWindow/WindowState: Saves window state (toolbar position etc.)
    Logging/Severity: Dictates logging severity
    Logging/Logfile: Which file should the software write logs to.
    """

    def __init__(self):
        super().__init__()
        self.globalSettings = QSettings()
        self.globalSettings.setValue("Program/Version", "v1.6.0")
        self.globalSettings.setValue("Program/TOR Profile Location",
                                     self.globalSettings.value("Program/TOR Profile Location", ""))
        self.globalSettings.setValue("Program/BaseDir",
                                     self.globalSettings.value("Program/BaseDir", "Unset"))

        # The value '20' equates to logging.INFO
        # It's not necessary to set this, but we will for
        #   the sake of completeness
        self.globalSettings.setValue("Logging/Severity",
                                     self.globalSettings.value("Logging/Severity", "20"))
        self.globalSettings.setValue("Logging/Logfile",
                                     self.globalSettings.value("Logging/Logfile",
                                                               str(Path.home() / 'LinkScope_logfile.log')))

        self.globalSettings.setValue("Program/Graph Layout",
                                     self.globalSettings.value("Program/Graph Layout", "dot"))
        self.globalSettings.setValue("Program/Graphics/Entity Text Font Type",
                                     self.globalSettings.value("Program/Graphics/Entity Text Font Type", "Mono"))
        self.globalSettings.setValue("Program/Graphics/Entity Text Font Size",
                                     self.globalSettings.value("Program/Graphics/Entity Text Font Size", "11"))
        self.globalSettings.setValue("Program/Graphics/Entity Text Font Boldness",
                                     self.globalSettings.value("Program/Graphics/Entity Text Font Boldness", "700"))
        self.globalSettings.setValue("Program/Graphics/Link Text Font Type",
                                     self.globalSettings.value("Program/Graphics/Link Text Font Type", "Mono"))
        self.globalSettings.setValue("Program/Graphics/Link Text Font Size",
                                     self.globalSettings.value("Program/Graphics/Link Text Font Size", "11"))
        self.globalSettings.setValue("Program/Graphics/Link Text Font Boldness",
                                     self.globalSettings.value("Program/Graphics/Link Text Font Boldness", "700"))
        self.globalSettings.setValue("Program/Graphics/Entity Text Color",
                                     self.globalSettings.value("Program/Graphics/Entity Text Color", "#000000"))
        self.globalSettings.setValue("Program/Graphics/Link Text Color",
                                     self.globalSettings.value("Program/Graphics/Link Text Color", "#000000"))
        self.globalSettings.setValue("Program/Graphics/Label Fade Scroll Distance",
                                     self.globalSettings.value("Program/Graphics/Label Fade Scroll Distance", "3"))

        self.globalSettings.setValue("Program/Usage/First Time Start",
                                     self.globalSettings.value("Program/Usage/First Time Start", True))

        self.globalSettings.setValue("Program/Sources/Sources List",
                                     self.globalSettings.value(
                                         "Program/Sources/Sources List",
                                         "{}"))

        self.setValue("Project/Name", "Untitled")
        self.setValue("Project/BaseDir", "")
        self.setValue("Project/FilesDir", "")
        # For any entity with a Path variable, this dictates whether a copy of the original is made or whether a
        #   symlink is created. Symlinks however require special permissions or developer mode in Windows.
        # To ensure that the software works out-of-the-box on all platforms, the default is set to 'Copy'.
        self.setValue("Project/Symlink or Copy Materials", "Copy")  # Values are 'Copy' or 'Symlink'.
        self.setValue("Project/Resolution Result Grouping Threshold", "15")
        self.setValue("Project/Number of Answers Returned", "3")
        self.setValue("Project/Question Answering Retriever Value", "10")
        self.setValue("Project/Question Answering Reader Value", "10")
        self.setValue("Project/Server/Project", "")
        self.setValue("Project/Server/Collectors", "{}")

    def getGroupSettings(self, settingsGroup: str) -> dict:
        if not settingsGroup.endswith('/'):
            settingsGroup += '/'
        settingsDict = {
            setting: self.globalSettings.value(setting)
            for setting in self.globalSettings.allKeys()
            if setting.startswith(settingsGroup)
        }
        for setting in self:
            if setting.startswith(settingsGroup):
                settingsDict[setting] = self[setting]
        return dict(sorted(settingsDict.items()))

    def setValue(self, key, value) -> None:
        if self.globalSettings.contains(key):
            self.globalSettings.setValue(key, value)
        self[key] = value

    def setGlobalValue(self, key, value) -> None:
        """
        Helper in the case we want to be explicit in setting a value globally.
        """
        self.globalSettings.setValue(key, value)

    def value(self, key, alt=None):
        if self.globalSettings.contains(key):
            return self.globalSettings.value(key)
        return self.get(key, alt)

    def removeKey(self, key) -> bool:
        try:
            if self.globalSettings.contains(key):
                self.globalSettings.remove(key)
            else:
                self.pop(key)
            return True
        except KeyError:
            return False

    def save(self) -> None:
        # Save and then move to prevent corruption if the application closes unexpectedly.
        actualSavePath = str(Path(self.value("Project/BaseDir")).joinpath(self.value("Project/Name") + ".linkscope"))
        if is_path_exists_or_creatable_portable(actualSavePath):
            tempSavePath = f'{actualSavePath}.tmp'
            with open(tempSavePath, "wb") as projectFile:
                dump(self, projectFile)
            move(tempSavePath, actualSavePath)
        self.globalSettings.sync()
        globalSettingsSavingError = self.globalSettings.status()
        if globalSettingsSavingError != self.globalSettings.Status.NoError:
            raise ValueError(f'Could not save global settings: {globalSettingsSavingError}')

    def load(self, savedDict: dict) -> None:
        # No need to do anything with global settings.
        for key in savedDict:
            self[key] = savedDict[key]
