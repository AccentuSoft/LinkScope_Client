#!/usr/bin/env python3


class GetWebsiteBody:
    # A string that is treated as the name of this resolution.
    name = "Get Website Body"

    # A string that describes this resolution.
    description = "Returns the contents of the body tag of the selected websites."

    originTypes = {'Website'}

    resultTypes = {'Phrase'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import requests

        headers = {
            'User-Agent': 'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        }

        returnResults = []

        for entity in entityJsonList:
            uid = entity['uid']

            primaryField = entity[list(entity)[1]]

            if primaryField.startswith('http://') or primaryField.startswith('https://'):
                url = primaryField
            else:
                url = 'http://' + primaryField

            r = requests.get(url, headers=headers)
            doc = r.text

            returnResults.append([{'Phrase': 'Website Body: ' + primaryField,
                                   'Notes': doc,
                                   'Entity Type': 'Phrase'},
                                  {uid: {'Resolution': 'Website Body', 'Notes': ''}}])
        return returnResults
