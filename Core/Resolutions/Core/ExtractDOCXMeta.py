#!/usr/bin/env python3


class ExtractDOCXMeta:
    # A string that is treated as the name of this resolution.
    name = "Get DOCX Metadata"
    category = "File Operations"

    # A string that describes this resolution.
    description = "Returns a set of nodes that contain all the metadata info of a docx file."

    originTypes = {'Document', 'Archive'}

    resultTypes = {'Phrase', 'Date'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        from docx2python import docx2python
        import magic
        from pathlib import Path

        returnResults = []

        for entity in entityJsonList:
            uid = entity['uid']
            filePath = Path(parameters['Project Files Directory']) / entity['File Path']

            if not (filePath.exists() and filePath.is_file()):
                continue

            if magic.from_file(str(filePath), mime=True) != \
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                continue  # We only care about docx files

            metadata = docx2python(filePath)

            data = metadata.properties
            defaultDateProperties = ['created', 'modified']

            modifiedDate = str(data.get('modified'))
            modifiedDate = modifiedDate.replace('Z', '')
            returnResults.append([{'Date': modifiedDate,
                                   'Entity Type': 'Date'},
                                  {uid: {'Resolution': 'modified', 'Notes': ''}}])
            createdDate = str(data.get('created'))
            createdDate = createdDate.replace('Z', '')
            returnResults.append([{'Date': createdDate,
                                   'Entity Type': 'Date'},
                                  {uid: {'Resolution': 'created', 'Notes': ''}}])

            for metadataKey in [dataKey for dataKey in data if dataKey not in defaultDateProperties]:
                returnResults.append([{'Phrase': metadataKey + ': ' + str(data.get(metadataKey)),
                                       'Entity Type': 'Phrase'},
                                      {uid: {'Resolution': metadataKey, 'Notes': ''}}])

        return returnResults
