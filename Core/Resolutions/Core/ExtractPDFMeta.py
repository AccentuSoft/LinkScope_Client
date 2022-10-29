#!/usr/bin/env python3


class ExtractPDFMeta:
    # A string that is treated as the name of this resolution.
    name = "Get PDF Metadata"
    category = "File Operations"

    # A string that describes this resolution.
    description = "Returns a set of nodes that contain all the metadata info of pdf files."

    originTypes = {'Document'}

    resultTypes = {'Phrase'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        from PyPDF2 import PdfFileReader
        import magic
        from pathlib import Path

        returnResults = []

        for entity in entityJsonList:
            uid = entity['uid']
            filePath = Path(parameters['Project Files Directory']) / entity['File Path']

            if not (filePath.exists() and filePath.is_file()):
                continue

            if magic.from_file(str(filePath), mime=True) != \
                    'application/pdf':
                continue

            with open(filePath, 'rb') as f:
                pdf = PdfFileReader(f)
                info = pdf.getDocumentInfo()
                number_of_pages = pdf.getNumPages()

            for metadataKey in info:
                if 'Date' in metadataKey:
                    try:
                        strDate = info[metadataKey]
                        strDate = strDate.split(':')[1].split('-')[0]
                        strDate1 = strDate[:-6]
                        strDate2 = strDate[-6:]
                        strDate2 = ':'.join(strDate2[i:i + 2] for i in range(0, 6, 2))
                        strDate1 = f'{strDate1[:-4]}-' + \
                                   '-'.join(strDate1[::-1][i: i + 2] for i in range(0, 4, 2))[::-1]
                        strDate = f'{strDate1}T{strDate2}'
                        returnResults.append([{'Date': strDate,
                                               'Entity Type': 'Date'},
                                              {uid: {'Resolution': metadataKey, 'Notes': ''}}])
                    except Exception:
                        # Reset strDate to default value
                        strDate = info[metadataKey]
                        returnResults.append([{'Date': strDate,
                                               'Entity Type': 'Date'},
                                              {uid: {'Resolution': metadataKey, 'Notes': ''}}])
                else:
                    returnResults.append([{'Phrase': f'{metadataKey}: {str(info[metadataKey])}',
                                           'Entity Type': 'Phrase'},
                                          {uid: {'Resolution': metadataKey, 'Notes': ''}}])

            returnResults.append([{'Phrase': f'Number of Pages: {str(number_of_pages)}', 'Entity Type': 'Phrase'},
                                  {uid: {'Resolution': 'Number of Pages', 'Notes': ''}}])

        return returnResults
