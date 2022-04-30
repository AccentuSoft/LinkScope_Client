#!/usr/bin/env python3

from msgpack import dump
from shutil import move
from pathlib import Path
from Core.PathHelper import is_path_exists_or_creatable_portable


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
        self.setValue("Program/BaseDir", "Unset")  # dirname(abspath(getsourcefile(lambda:0))) + "/../" )
        self.setValue("Program/GraphLayout", "dot")
        self.setValue("Program/EntityTextFontType", "Mono")
        self.setValue("Program/EntityTextFontSize", "11")
        self.setValue("Program/EntityTextFontBoldness", "700")
        self.setValue("Program/LinkTextFontType", "Mono")
        self.setValue("Program/LinkTextFontSize", "11")
        self.setValue("Program/LinkTextFontBoldness", "700")
        self.setValue("Program/EntityTextColor", "#000000")  # RGB
        self.setValue("Program/LinkTextColor", "#000000")  # RGB
        self.setValue("Project/Name", "Untitled")
        self.setValue("Project/BaseDir", "")
        self.setValue("Project/FilesDir", "")
        # For any entity with a Path variable, this dictates whether a copy of the original is made or whether a
        #   symlink is created. Symlinks require special permissions or developer mode in Windows however.
        # To ensure that the software works out-of-the-box on all platforms, the default is set to 'Copy'.
        self.setValue("Project/Symlink or Copy Materials", "Copy")  # Values are 'Copy' or 'Symlink'.
        self.setValue("Project/Resolution Result Grouping Threshold", "15")
        self.setValue("Project/Number of Answers Returned", "3")
        self.setValue("Project/Question Answering Retriever Value", "10")
        self.setValue("Project/Question Answering Reader Value", "10")
        self.setValue("Project/Server/Project", "")
        self.setValue("Project/Server/Collectors", "")

        # The value '20' equates to logging.INFO
        # It's not necessary to set this, but we will for
        #   the sake of completeness
        self.setValue("Logging/Severity", "20")
        self.setValue("Logging/Logfile", str(Path.home() / 'LinkScope_logfile.log'))

    # Usability Alias
    def setValue(self, key, value):
        self[key] = value

    def value(self, key, alt=None):
        return self.get(key, alt)

    def save(self):
        # Save and then move to prevent corruption if the application closes unexpectedly.
        actualSavePath = str(Path(self.value("Project/BaseDir")).joinpath(self.value("Project/Name") + ".linkscope"))
        if is_path_exists_or_creatable_portable(actualSavePath):
            tempSavePath = actualSavePath + '.tmp'
            projectFile = open(tempSavePath, "wb")
            dump(self, projectFile)
            projectFile.close()
            move(tempSavePath, actualSavePath)

    def load(self, savedDict: dict):
        for key in savedDict:
            self[key] = savedDict[key]
