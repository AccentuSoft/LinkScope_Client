#!/usr/bin/env python3


class ThreatInfo:
    # A string that is treated as the name of this resolution.
    name = "Pulsedive Threat Lookup"

    # A string that describes this resolution.
    description = "Returns Nodes of Threat Info"

    originTypes = {'Phrase'}

    resultTypes = {'Phrase, Website'}

    parameters = {'Pulsedive API Key': {
        'description': 'Enter your API Key. If you do not have one, the resolution will not return any results.\n'
                       'Standard Free API limits: 30 requests per minute, and 1,000 requests per day.\n'
                       'If you exceed the limits, no results will be returned.\n'
                       'For more information on API premium plans visit:\n'
                       'https://pulsedive.com/about/api',
        'type': 'String',
        'value': '',
        'global': True},
        'Max Articles': {
            'description': 'The resolution returns a number of articles associated with the threat.\n'
                           'Please enter the maximum number of webpages to return.\n'
                           'Enter "0" (no quotes) to return everything.',
            'type': 'String',
            'value': '',
            'default': '10'}}

    def resolution(self, entityJsonList, parameters):
        import requests
        returnResults = []
        try:
            linkNumbers = int(parameters['Max Articles'])
        except ValueError:
            return "Invalid integer value specified for Max Articles."
        if linkNumbers < 0:
            return []

        for entity in entityJsonList:
            uid = entity['uid']

            search_term = entity[list(entity)[1]]
            api_key = parameters['Pulsedive API Key']
            try:
                r = requests.get(
                    f'https://pulsedive.com/api/info.php?threat={search_term}&pretty=1&key={api_key}')
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"

            if r.status_code == 429:
                return []
            if r.status_code == 404:
                return []

            data = r.json()

            returnResults.append([{'Phrase': 'category: ' + data["category"],
                                   'Entity Type': 'Phrase'},
                                  {uid: {'Resolution': 'Category',
                                         'Notes': ''}}])
            returnResults.append([{'Phrase': 'risk: ' + data["risk"],
                                   'Entity Type': 'Phrase'},
                                  {uid: {'Resolution': 'Risk',
                                         'Notes': ''}}])

            if linkNumbers == 0:
                linkNumbers = int(len(data["news"]))
            elif linkNumbers >= len(data["news"]):
                linkNumbers = int(len(data["news"]))

            for i in range(linkNumbers):
                returnResults.append([{'URL': data["news"][i]['link'],
                                       'Date Created': data["news"][i]['stamp'].replace(' ', 'T'),
                                       'Entity Type': 'Website'},
                                      {uid: {'Resolution': 'Related Article',
                                             'Notes': ''}}])

            if not data["summary"]["attributes"]:
                continue
            else:
                for key in data["summary"]["attributes"]["technology"].keys():
                    returnResults.append([{'Phrase': key,
                                           'Entity Type': 'Phrase'},
                                          {uid: {'Resolution': 'Technologies Used',
                                                 'Notes': ''}}])

                for key in data["summary"]["attributes"]["protocol"].keys():
                    returnResults.append([{'Phrase': key,
                                           'Entity Type': 'Phrase'},
                                          {uid: {'Resolution': 'Protocols Used',
                                                 'Notes': ''}}])

        return returnResults
