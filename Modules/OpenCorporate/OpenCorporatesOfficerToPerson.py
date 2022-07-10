#!/usr/bin/env python3


class OpenCorporatesOfficerToPerson:
    name = "OpenCorporates Officer to Person Conversion"

    category = "OpenCorporates"

    description = "Convert Open Corporates Officer Entities to Person Entities."

    originTypes = {'Open Corporates Officer'}

    resultTypes = {'Person'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        returnResults = []
        for entity in entityJsonList:
            uid = entity['uid']
            returnResults.append([{'Full Name': entity['Full Name and ID'].split(' | ')[0],
                                   'Occupation': entity['Occupation'],
                                   'Entity Type': 'Person'},
                                  {uid: {'Resolution': 'OpenCorporates Officer to Person',
                                         'Notes': ''}}])

        return returnResults
