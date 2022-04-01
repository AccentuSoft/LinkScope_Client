#!/usr/bin/env python3


class EmailToPhrase:
    name = "Email Username To Phrase"
    category = "String Operations"
    description = "Get the username associated with the given email address."
    originTypes = {'Email Address'}
    resultTypes = {'Phrase'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):

        returnResults = []

        for entity in entityJsonList:
            primaryField = entity['Email Address']
            returnResults.append([{'Phrase': primaryField.split('@')[0],
                                   'Entity Type': 'Phrase'},
                                  {entity['uid']: {'Resolution': 'Email Username To Phrase',
                                                   'Notes': ''}}])

        return returnResults
