#!/usr/bin/env python3


class ExtractDateCreated:
    name = "Extract Date Created"
    category = "Date Operations"
    description = "Extract the date in the Date Created field of the selected entities."
    originTypes = {'*'}
    resultTypes = {'Date'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):

        return_result = []

        for entity in entityJsonList:
            uid = entity['uid']
            return_result.append([{'Date': str(entity['Date Created']),
                                   'Entity Type': 'Date'},
                                  {uid: {'Resolution': 'Extract Dates', 'Notes': ''}}])
        return return_result
