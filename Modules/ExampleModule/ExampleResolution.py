#!/usr/bin/env python3

class ExampleResolution:
    # A string that is treated as the name of this resolution.
    name = "Example Resolution"

    # A string that describes this resolution.
    description = "Resolves Nothing in particular"

    # A set of entities that this resolution can be ran on.
    originTypes = {'Person'}

    # A set of entities that could be the result of this resolution.
    resultTypes = {'Person'}

    # A dictionary of properties for this resolution. The key is the property name,
    # the value is the property attributes. The type of input expected from the user is determined by the
    # variable type of the 'value' parameter.
    parameters = {'String Example': {'description': 'Example String Description',
                                     'type': 'String',
                                     'value': ''},

                  'File Example': {'description': 'Example Choose File Description',
                                   'type': 'File',
                                   'value': ''},

                  'Choose One Example': {'description': 'Example Choose One Description',
                                         'type': 'SingleChoice',
                                         'value': {'one', 'two', 'three'}
                                         },

                  'Choose Multiple Example': {'description': 'Example Choose Multiple Description',
                                              'type': 'MultiChoice',
                                              'value': {'one', 'two', 'three'}
                                              }
                  }

    def resolution(self, entityJsonList, parameters):
        """
        eJsonList is a dictionary where the keys are the accepted origin
        types, and the values are lists of json representations of
        entities whose type matches the key.

        parameters is a dictionary with the keys of the 'parameters' variable.
        The value of each key is the user's input.

        Example:
        If the origin types of an entity are: {'Person', 'Alias'}

        The input could be:
        [Person1JSON, Person2JSON]

        or:

        [Person1JSON, Alias1JSON]

        Returns a list of lists, where each inner list contains an entity produced as output, and a dict of dicts
        where the keys of the outer dictionary are either UIDs of input nodes or indices of elements in the outer list.
        The inner dict holds the 'Resolution' and 'Notes' characteristics of the link to create.

        Example:

        [[resultNodeJson1, {'inputNodeUID1': {'Resolution': 'LinkName1', 'Notes': 'LinkNotes1'},
                            resultNodeIndex1: {'Resolution': 'LinkName2', 'Notes': ''}}],
        ...]
        """
        return []
