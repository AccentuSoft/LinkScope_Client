#!/usr/bin/env python3


class RegexMatch:
    # A string that is treated as the name of this resolution.
    name = "Get Regex Match"

    # A string that describes this resolution.
    description = "Extract text from Phrases and Websites with Regular Expressions."

    originTypes = {'Phrase', 'Website'}

    resultTypes = {'Phrase'}

    parameters = {'Regex Match': {'description': "Please enter the Regex expression to extract strings with.",
                                  'type': 'String',
                                  'value': ''},
                  'Max Results': {'description': 'Please enter the Maximum number of Results to return.',
                                  'type': 'String',
                                  'value': '',
                                  'default': '5'},
                  'Re Flags': {'description': 'Select the Regex Flags to be used.',
                               'type': 'MultiChoice',
                               'value': {'re.I', 're.M', 're.S'}
                               }
                  }

    def resolution(self, entityJsonList, parameters):
        import re
        import requests

        headers = {
            'User-Agent': 'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0',
        }

        returnResults = []
        try:
            maxResults = int(parameters['Max Results'])
        except ValueError:
            return "Invalid integer provided in 'Max Results' parameter"
        if maxResults <= 0:
            return []
        search_param = parameters['Regex Match']
        flags = parameters['Re Flags']

        flagsToUse = 0
        for flag in flags:
            flagsToUse |= flag

        for entity in entityJsonList:
            uid = entity['uid']
            if entity['Entity Type'] == 'Phrase':
                text = str(entity['Notes']) + "\n" + str(entity['Phrase'])
            else:  # Website entity
                r = requests.get(entity["URL"], headers=headers)
                text = r.text

            search_re = re.findall(search_param, text, flags=flagsToUse)

            for regexMatch in search_re[:maxResults]:
                returnResults.append([{'Phrase': 'Regex Match: ' + regexMatch,
                                       'Entity Type': 'Phrase',
                                       'Notes': ''},
                                      {uid: {'Resolution': 'Regex String Match',
                                             'Notes': ''}}])
        return returnResults
