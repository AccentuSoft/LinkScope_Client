#!/usr/bin/env python3


class ExtractPDFMeta:
    # A string that is treated as the name of this resolution.
    name = "Get PDF Metadata"
    category = "File Operations"

    # A string that describes this resolution.
    description = "Returns a set of nodes that contain notable metadata info of pdf files."

    originTypes = {'Document'}

    resultTypes = {'Phrase'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        from pypdf import PdfReader
        from datetime import datetime, timedelta
        import magic
        from pathlib import Path

        returnResults = []

        for entity in entityJsonList:
            uid = entity['uid']
            filePath = Path(parameters['Project Files Directory']) / entity['File Path']

            if not (filePath.exists() and filePath.is_file()):
                continue

            if magic.from_file(str(filePath), mime=True) != 'application/pdf':
                continue

            with open(filePath, 'rb') as f:
                pdf = PdfReader(f)
                info = pdf.metadata
                number_of_pages = len(pdf.pages)

            for metadataKey in info:
                if metadataKey.startswith('/'):
                    attrValue = metadataKey[1:]
                else:
                    attrValue = metadataKey
                if 'Date' in metadataKey:
                    try:
                        strDate = info[metadataKey].split(':', 1)[1]
                        if strDate.endswith('Z'):
                            dateString = datetime.strptime(strDate, "%Y%m%d%H%M%SZ").isoformat()
                        elif '+' in strDate:
                            datePart1, datePart2 = strDate.split('+', 1)
                            date1 = datetime.strptime(datePart1, "%Y%m%d%H%M%S")
                            date2 = timedelta(hours=int(datePart2.split("'")[0]), minutes=int(datePart2.split("'")[1]))
                            dateString = (date1 + date2).isoformat()
                        elif '-' in strDate:
                            datePart1, datePart2 = strDate.split('-', 1)
                            date1 = datetime.strptime(datePart1, "%Y%m%d%H%M%S")
                            date2 = timedelta(hours=int(datePart2.split("'")[0]), minutes=int(datePart2.split("'")[1]))
                            dateString = (date1 - date2).isoformat()
                        else:
                            raise ValueError('Cannot parse Date format.')

                        returnResults.append([{'Date': dateString,
                                               'Entity Type': 'Date'},
                                              {uid: {'Resolution': attrValue, 'Notes': ''}}])
                    except Exception:
                        # Reset strDate to default value
                        strDate = info[metadataKey]
                        returnResults.append([{'Date': strDate,
                                               'Entity Type': 'Date'},
                                              {uid: {'Resolution': attrValue, 'Notes': ''}}])
                else:
                    # Clean some misshapen strings
                    value = str(info[metadataKey])
                    if value.startswith('/'):
                        value = value[1:]

                    returnResults.append([{'Phrase': f'{attrValue}: {value}',
                                           'Entity Type': 'Phrase'},
                                          {uid: {'Resolution': attrValue, 'Notes': ''}}])

            returnResults.append([{'Phrase': f'Number of Pages: {number_of_pages}', 'Entity Type': 'Phrase'},
                                  {uid: {'Resolution': 'Number of Pages', 'Notes': ''}}])

        return returnResults
