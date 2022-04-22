#!/usr/bin/env python3


class WebsiteFromPhrase:
    name = "Website From Phrase"
    category = "String Operations"
    description = "Extract website-like objects from a phrase."
    originTypes = {'Phrase'}
    resultTypes = {'Domain'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import re

        websiteRegex = re.compile(r"""^https?://(\S(?<!\.)){1,63}(\.(\S(?<!\.)){1,63})+$""")
        wordChar = re.compile(r'\w')

        returnResults = []

        for entity in entityJsonList:
            primaryField = entity['Phrase']
            for entityChunk in primaryField.split():
                while wordChar.match(entityChunk[-1]) is None:
                    entityChunk = entityChunk[:-1]
                if websiteRegex.match(entityChunk):
                    returnResults.append([{'URL': primaryField,
                                           'Entity Type': 'Website'},
                                          {entity['uid']: {'Resolution': 'Phrase To Website',
                                                           'Notes': ''}}])

        return returnResults
