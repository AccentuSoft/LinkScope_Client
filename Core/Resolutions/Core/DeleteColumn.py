#!/usr/bin/env python3


class DeleteColumn:
    # A string that is treated as the name of this resolution.
    name = "Rename or Delete Column"

    category = "Spreadsheet Operations"

    # A string that describes this resolution.
    description = "Deletes the column with the specified index from a Spreadsheet document."

    originTypes = {'Spreadsheet'}

    resultTypes = {'Spreadsheet'}

    parameters = {'Working Sheet': {'description': 'The name or index of the Sheet to read in the Spreadsheet '
                                                   'file. By default, the first Sheet is used.',
                                    'type': 'String',
                                    'value': '0',
                                    'default': '0'},
                  'Column Name to Rename': {'description': 'Please enter the name of the column that you wish to  '
                                                           'rename or delete.',
                                            'type': 'String',
                                            'value': ''},
                  'New Column Name': {'description': 'Please enter the new name for the column.\nEnter the same name '
                                                     'to delete the column instead.',
                                      'type': 'String',
                                      'value': ''}
                  }

    def resolution(self, entityJsonList, parameters):
        from pathlib import Path
        import pandas as pd
        import contextlib

        workingSheet = parameters['Working Sheet']
        with contextlib.suppress(ValueError):
            workingSheet = int(workingSheet)

        renameColumn = parameters['Column Name to Rename']
        targetColumn = parameters['New Column Name']

        returnResults = []

        for entity in entityJsonList:
            uid = entity['uid']
            filePath = Path(parameters['Project Files Directory']) / entity['File Path']
            if not filePath.exists() or not filePath.is_file():
                continue

            try:
                csvDF = pd.read_excel(filePath, sheet_name=workingSheet)
            except ValueError:
                continue

            if renameColumn == targetColumn:
                csvDF.drop(renameColumn, inplace=True)
            else:
                csvDF.rename(columns={renameColumn: targetColumn}, inplace=True)

            count = 0
            while True:
                newFileName = f"{filePath.name.split(filePath.suffix, 1)[0]}-c{count}{filePath.suffix}"
                newFilePath = filePath.parent / newFileName
                if not newFilePath.exists():
                    break
            csvDF.to_excel(newFilePath, index=False)

            returnResults.append([{'Spreadsheet Name': newFileName,
                                   'File Path': newFileName,
                                   'Entity Type': 'Spreadsheet'},
                                  {uid: {'Resolution': 'Rename/Delete Column',
                                         'Notes': ''}}])

        return returnResults
