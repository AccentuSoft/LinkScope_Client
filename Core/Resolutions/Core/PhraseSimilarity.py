#!/usr/bin/env python3

class PhraseSimilarity:
    name = "Perform Similarity Check"
    description = "Find the ration of similarity between two strings"
    originTypes = {'*'}
    resultTypes = {'Phrase'}
    parameters = {'Primary field or Notes': {'description': 'Choose Either Primary field or Notes',
                                             'type': 'SingleChoice',
                                             'value': {'Notes', 'Primary Field'}},
                  'Algorithm': {'description': 'Select the Algorithm to use',
                                'type': 'SingleChoice',
                                'value': {'levenshtein distance', 'damerau levenshtein distance',
                                          'jaro distance', 'jaro winkler similarity',
                                          'match rating comparison', 'hamming distance'}}
                  }

    def resolution(self, entityJsonList, parameters):
        import jellyfish
        from itertools import combinations

        return_result = []
        primary_fields = []
        notes_fields = []
        uidList = []
        selection = parameters['Primary field or Notes']
        algorithm = parameters['Algorithm'].replace(" ", "_")
        for entity in entityJsonList:
            uidList.append(entity['uid'])
            if selection == 'Primary Field':
                primary_fields.append(entity[list(entity)[1]].strip())
            elif selection == 'Notes':
                notes_fields.append(entity['Notes'])

        if selection == "Notes" and len(notes_fields) > 1:
            value = list(combinations(notes_fields, 2))
            uid = list(combinations(uidList, 2))
        elif selection == "Primary Field" and len(primary_fields) > 1:
            value = list(combinations(primary_fields, 2))
            uid = list(combinations(uidList, 2))
        else:
            return "Please Select 2 or more entities for comparison"
        for field in value:
            similarity = getattr(jellyfish, algorithm)(field[0], field[1])
            return_result.append([{'Phrase': f"{similarity} similarity",
                                   'Entity Type': 'Phrase'},
                                  {uid[value.index(field)][0]: {'Resolution': 'Notes Word Counter', 'Notes': ''}}])
            return_result.append([{'Phrase': f"{similarity} similarity",
                                   'Entity Type': 'Phrase'},
                                  {uid[value.index(field)][1]: {'Resolution': 'Notes Word Counter', 'Notes': ''}}])

        return return_result
