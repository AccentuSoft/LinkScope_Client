#!/usr/bin/env python3


class RegexMatch:
    # A string that is treated as the name of this resolution.
    name = "Get Regex Match"

    # A string that describes this resolution.
    description = "Returns Nodes of contact info for websites"

    originTypes = {'Phrase', 'Website'}

    resultTypes = {'Phrase'}

    parameters = {'Regex Match': {'description': "Please enter the Regex to be searched for.\n"
                                                 "if any matches are found to be exactly the same as the entity's "
                                                 "primary field they will be ignored",
                                  'type': 'String',
                                  'value': ''},
                  'Max Results': {'description': 'Please enter the Maximum number of Results to return',
                                  'type': 'String',
                                  'value': ''},
                  'Re Flags': {'description': 'Select Re Flags to be used while compiling the regex',
                               'type': 'MultiChoice',
                               'value': {'re.I', 're.M', 're.S'}
                               }
                  }

    def resolution(self, entityJsonList, parameters):
        import re
        import requests

        headers = {
            'User-Agent': 'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        }

        returnResults = []
        linkNumbers = int(parameters['Max Results'])
        search_param = parameters['Regex Match']
        flags = parameters['Re Flags']
        print(flags)

        for entity in entityJsonList:
            uid = entity['uid']
            if entity['Entity Type'] == 'Phrase':
                text = str(entity['Notes']) + str(entity['Phrase'])
            else:  # Website entity
                r = requests.get(entity["URL"], headers=headers)
                text = r.text

            if len(flags) == 3:
                search_re = re.findall(search_param, text, flags=re.I | re.S | re.M)
            elif len(flags) == 2:
                search_re = re.findall(search_param, text, flags=flags[0] | flags[1])
            elif len(flags) == 1:
                search_re = re.findall(search_param, text, flags=flags[0])
            else:
                search_re = re.findall(search_param, text)

            if linkNumbers > len(search_re):
                linkNumbers = int(len(search_re))

            for i in range(linkNumbers):
                if search_re[i] == entity[list(entity)[1]]:
                    continue
                returnResults.append([{'Phrase': search_re[i],
                                       'Entity Type': 'Phrase',
                                       'Notes': ''},
                                      {uid: {'Resolution': 'Phrase Details',
                                             'Notes': ''}}])
        return returnResults
