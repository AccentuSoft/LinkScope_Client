#!/usr/bin/env python3


class ToPhrase:
    name = "Convert To Phrase"
    description = "Convert the primary field of selected entities to a Phrase entity."
    originTypes = {'*'}
    resultTypes = {'Phrase'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):

        returnResults = []

        for entity in entityJsonList:
            primaryField = entity[list(entity)[1]]
            returnResults.append([{'Phrase': primaryField,
                                   'Entity Type': 'Phrase'},
                                  {entity['uid']: {'Resolution': 'To Phrase',
                                                   'Notes': ''}}])

        return returnResults
