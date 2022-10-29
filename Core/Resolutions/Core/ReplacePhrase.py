#!/usr/bin/env python3


class ReplacePhrase:
    name = "Replace String in Phrase"
    category = "String Operations"
    description = "Replace a character, or sequence of characters in a Phrase with another character or sequence."
    originTypes = {'Phrase'}
    resultTypes = {'Phrase'}

    parameters = {'Sequence to Remove': {'description': 'Specify the character or sequence of characters to replace.',
                                         'type': 'String',
                                         'value': ''
                                         },
                  'Sequence to Insert': {'description': 'Specify the character or sequence of characters to replace '
                                                        'the old character or sequence with. Enter the same character '
                                                        'or sequence to delete the character or sequence instead.',
                                         'type': 'String',
                                         'value': ''
                                         },
                  'Match Type': {'description': 'Specify whether the matching of characters to replace '
                                                'should be plain (as in, match characters as they were typed), '
                                                'case insensitive, or regex.',
                                 'type': 'SingleChoice',
                                 'value': {'Plain', 'Case Insensitive', 'Regex'},
                                 'default': 'Plain'
                                 },
                  'Match Count': {'description': 'Specify the number of times to replace the specified character or '
                                                 'sequence with the new sequence. Zero is unlimited times.',
                                  'type': 'String',
                                  'value': '0',
                                  'default': '0'
                                  }
                  }

    def resolution(self, entityJsonList, parameters):
        import re

        returnResults = []

        remove = parameters['Sequence to Remove']
        insert = parameters['Sequence to Insert']
        if insert == remove:
            insert = ''
        matchType = parameters['Match Type']

        try:
            matchCount = int(parameters['Match Count'])
            if matchCount < 0:
                return []
        except ValueError:
            return "Invalid Match Count specified."

        for entity in entityJsonList:
            primaryField = entity['Phrase']

            if matchType == 'Plain':
                if matchCount == 0:
                    matchCount = -1
                primaryField = primaryField.replace(remove, insert, matchCount)
            elif matchType == 'Case Insensitive':
                pattern = re.compile(re.escape(remove), re.IGNORECASE)
                primaryField = pattern.sub(insert, primaryField, matchCount)
            else:
                pattern = re.compile(remove)
                primaryField = pattern.sub(insert, primaryField, matchCount)

            returnResults.append([{'Phrase': primaryField,
                                   'Entity Type': 'Phrase'},
                                  {entity['uid']: {'Resolution': 'Replace characters',
                                                   'Notes': ''}}])

        return returnResults
