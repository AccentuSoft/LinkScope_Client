#!/usr/bin/env python3


class OpenCorporatesCorporationToCorporation:
    name = "OpenCorporates Company to Company Conversion"

    category = "OpenCorporates"

    description = "Convert Open Corporates Company Entities to Company Entities."

    originTypes = {'Open Corporates Company'}

    resultTypes = {'Company', 'Date'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        returnResults = []
        for entity in entityJsonList:
            uid = entity['uid']
            index_of_child = len(returnResults)
            companyStatus = entity['Current Status'].lower()
            returnResults.append(
                [{'Company Name': entity['Company Name'],
                  'Registration Number': entity['Company Number'],
                  'Entity Type': 'Company'},
                 {uid: {'Resolution': 'Company', 'Notes': ''}}])
            returnResults.append(
                [{'Date': entity['Incorporation Date'],
                  'Entity Type': 'Date'},
                 {index_of_child: {'Resolution': 'Incorporation Date', 'Notes': 'Incorporation Date'}}])
            if companyStatus == 'dissolved' or companyStatus == 'removed':
                returnResults.append(
                    [{'Date': entity.get('Dissolution Date'),
                      'Entity Type': 'Date'},
                     {index_of_child: {'Resolution': 'Dissolution Date', 'Notes': 'Dissolution Date'}}])

        return returnResults
