#!/usr/bin/env python3

"""
Credit:
https://twitter.com/bee_sec_san
https://github.com/HashPals/Name-That-Hash
"""


class NameThatHash:
    # A string that is treated as the name of this resolution.
    name = "Identify Hash Type"

    category = "String Operations"

    # A string that describes this resolution.
    description = "Identifies the algorithm that was used to generate the hash given as input."

    # A set of entities that this resolution can be ran on.
    originTypes = {'Hash', 'Phrase'}

    # A set of entities that could be the result of this resolution.
    resultTypes = {'Phrase'}

    # A dictionary of properties for this resolution. The key is the property name,
    # the value is the property attributes. The type of input expected from the user is determined by the
    # variable type of the 'value' parameter.
    parameters = {'Max Results Per Hash': {'description': 'Please enter the maximum results you want per hash. Results '
                                                          'are returned in order of likeliness, so the first few '
                                                          'results would be the hash types that would match the input '
                                                          'the best.',
                                           'type': 'String',
                                           'value': '',
                                           'default': '5'},

                  'Hash Crack Options': {'description': 'Please select whether you want to generate entities that '
                                                        'specify the appropriate configuration option to use in hash '
                                                        'cracking software for each hash type.',
                                         'type': 'MultiChoice',
                                         'value': {'HashCat', 'John'},
                                         'default': {'HashCat', 'John'}
                                         }
                  }

    def resolution(self, entityJsonList, parameters):
        from name_that_hash import check_hashes, hash_namer, hashes
        import logging

        nth = hash_namer.Name_That_Hash(hashes.prototypes)
        hashChecker = check_hashes.HashChecker({}, nth)

        try:
            maxResults = int(parameters['Max Results Per Hash'])
            if maxResults < 1:
                raise ValueError()
        except ValueError:
            return "Invalid integer provided for 'Max Results Per Hash' parameter: Input needs to be a positive " \
                   "integer that is bigger than 1."

        returnResults = []

        for entity in entityJsonList:
            uid = entity['uid']
            if entity['Entity Type'] == 'Hash':
                hashChecker.single_hash(entity['Hash Value'])
            elif entity['Entity Type'] == 'Phrase':
                hashChecker.single_hash(entity['Phrase'])
            else:
                continue

            try:
                output = hashChecker.output[0]
                resultsJson = output.get_prototypes()[:maxResults]
                for count, result in enumerate(resultsJson, start=1):
                    childIndex = len(returnResults)
                    resultString = str(count) + ") " + result['name']
                    description = result.get('description') if result.get('description') is not None else ''

                    returnResults.append([{'Phrase': resultString,
                                           'Entity Type': 'Phrase',
                                           'Notes': description},
                                          {uid: {'Resolution': 'Name That Hash'}}])

                    hashcat = str(result.get('hashcat'))
                    john = str(result.get('john'))

                    if hashcat is not None and 'HashCat' in parameters['Hash Crack Options']:
                        hashCatString = 'HashCat Option: ' + hashcat
                        returnResults.append([{'Phrase': hashCatString,
                                               'Entity Type': 'Phrase'},
                                              {childIndex: {'Resolution': 'HashCat Crack Option'}}])
                    if john is not None and 'John' in parameters['Hash Crack Options']:
                        johnString = 'John Option: ' + john
                        returnResults.append([{'Phrase': johnString,
                                               'Entity Type': 'Phrase'},
                                              {childIndex: {'Resolution': 'John Crack Option'}}])
            except IndexError:
                pass

        # The module will enable logging, and we will remove it here.
        rootLogger = logging.getLogger()
        for handler in rootLogger.handlers:
            rootLogger.removeHandler(handler)

        return returnResults
