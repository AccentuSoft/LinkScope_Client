#!/usr/bin/env python3


class ContainsPhrase:
    # A string that is treated as the name of this resolution.
    name = "Contains Phrase"

    category = "String Operations"

    # A string that describes this resolution.
    description = "Checks if a Phrase exists in the Notes of a Phrase entity or the body of a Website."

    originTypes = {'Phrase', 'Website'}

    resultTypes = {'Phrase'}

    parameters = {'Phrase to Search for': {'description': 'Please enter the Phrase to be searched for. Note that the '
                                                          'search is performed in the "Notes" field of a Phrase or the '
                                                          'body of the selected Website entities, not their primary '
                                                          'fields.',
                                           'type': 'String',
                                           'value': ''},
                  'Case Sensitive': {'description': 'Do you want the phrase to be case sensitive?',
                                     'type': 'SingleChoice',
                                     'value': {'Yes', 'No'}
                                     }
                  }

    def resolution(self, entityJsonList, parameters):
        import requests
        import re

        headers = {
            'User-Agent': 'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0',
        }

        returnResults = []

        for entity in entityJsonList:
            offsets = []
            counter = 0
            searchPhrase = parameters['Phrase to Search for']
            uid = entity['uid']
            if entity['Entity Type'] == 'Phrase':
                text = str(entity.get('Notes'))
                primaryField = entity['Phrase']
            else:  # Website entity
                request = requests.get(entity["URL"], headers=headers)
                primaryField = entity['URL']
                text = request.text

            if parameters['Case Sensitive'] == 'No':
                iterator = re.finditer(rf"{searchPhrase}", text, re.IGNORECASE)
                for match in iterator:
                    offsets.append(match.start())
                    counter += 1
            elif parameters['Case Sensitive'] == 'Yes':
                iterator = re.finditer(rf"{searchPhrase}", text)
                for match in iterator:
                    offsets.append(match.start())
                    counter += 1

            if counter > 0:
                returnResults.append([{'Phrase': primaryField + ' Contains Phrase: "' + searchPhrase +
                                                 f'" {counter} times',
                                       'Entity Type': 'Phrase',
                                       'Notes': f'"{searchPhrase}" was found {counter} time(s)\n'
                                                f'Offsets: Matches at character indices: '
                                                f'{(", ".join(map(str, offsets)))}'},
                                      {uid: {'Resolution': 'Contains Phrase ' + searchPhrase,
                                             'Notes': ''}}])

        return returnResults
