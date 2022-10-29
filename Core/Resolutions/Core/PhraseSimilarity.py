#!/usr/bin/env python3

class PhraseSimilarity:
    name = "String Similarity Check"
    category = "String Operations"
    description = "Find the ratio of similarity between two strings."
    originTypes = {'*'}
    resultTypes = {'Phrase'}
    parameters = {'Primary field or Notes': {'description': 'Choose Either Primary field or Notes',
                                             'type': 'SingleChoice',
                                             'value': {'Notes', 'Primary Field'}},
                  'Algorithm': {'description': 'Select the Algorithm to use',
                                'type': 'SingleChoice',
                                'value': {'levenshtein distance', 'damerau levenshtein distance',
                                          'jaro distance', 'jaro winkler similarity', 'hamming distance'}}
                  }

    def resolution(self, entityJsonList, parameters):
        import jellyfish
        from itertools import combinations

        return_result = []
        entity_fields = []
        selection = parameters['Primary field or Notes']
        algorithm = parameters['Algorithm'].replace(" ", "_")
        for entity in entityJsonList:
            if selection == 'Primary Field':
                entity_fields.append((entity['uid'], entity[list(entity)[1]].strip()))
            elif selection == 'Notes':
                entity_fields.append((entity['uid'], entity.get('Notes')))

        if len(entity_fields) < 2:
            return "Please Select 2 or more entities for comparison"
        for combination in combinations(entity_fields, 2):
            stringA = combination[0][1]
            uidA = combination[0][0]
            stringB = combination[1][1]
            uidB = combination[1][0]
            similarity = getattr(jellyfish, algorithm)(stringA, stringB)
            return_result.append([{'Phrase': f'{algorithm} between "{stringA}" and "{stringB}": {similarity}',
                                   'Entity Type': 'Phrase'},
                                  {uidA: {'Resolution': f'String Similarity for "{stringA}" and "{stringB}"',
                                          'Notes': ''},
                                   uidB: {'Resolution': f'String Similarity for "{stringA}" and "{stringB}"',
                                          'Notes': ''}}])

        return return_result
