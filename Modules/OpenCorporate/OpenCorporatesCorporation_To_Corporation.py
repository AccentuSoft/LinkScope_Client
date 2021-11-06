#!/usr/bin/env python3


class OpenCorporatesCorporation_To_Corporation:
    name = "OpenCorporateCompany to Company"

    description = "OpenCorporateCompany Entity to Company Entity"

    originTypes = {'Open Corporate Company'}

    resultTypes = {'Company, Date'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        returnResults = []
        for entity in entityJsonList:
            uid = entity['uid']
            index_of_child = len(returnResults)
            returnResults.append(
                [{'Company Name': entity[list(entity)[2]],
                  'Entity Type': 'Company'},
                 {uid: {'Resolution': 'Company', 'Notes': ''}}])
            returnResults.append(
                [{'Date': entity[list(entity)[5]],
                  'Entity Type': 'Date'},
                 {index_of_child: {'Resolution': 'Incorporation Date', 'Notes': 'Incorporation Date'}}])
            if entity[list(entity)[3]] == 'Dissolved' or entity[list(entity)[3]] == 'Removed':
                returnResults.append(
                    [{'Date': entity[list(entity)[6]],
                      'Entity Type': 'Date'},
                     {index_of_child: {'Resolution': 'Dissolution Date', 'Notes': 'Dissolution Date'}}])

        return returnResults
