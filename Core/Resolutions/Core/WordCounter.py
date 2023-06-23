#!/usr/bin/env python3


class WordCounter:
    name = "Get Number Of Words"
    category = "String Operations"
    description = "Count the number of words in a given phrase."
    originTypes = {'Phrase'}
    resultTypes = {'Phrase'}
    parameters = {'Primary field or Notes': {'description': 'Choose Either Primary field or Notes',
                                             'type': 'SingleChoice',
                                             'value': {'Notes', 'Primary Field'},
                                             'default': 'Notes'}}

    def resolution(self, entityJsonList, parameters):
        import re

        return_result = []
        selection = parameters['Primary field or Notes']
        for entity in entityJsonList:
            uid = entity['uid']
            if selection == "Notes":
                total = len(re.findall(r'\w+', entity['Notes'].strip()))
            else:
                total = len(re.findall(r'\w+', entity["Phrase"].strip()))
            return_result.append([{'Phrase': f"{total} words",
                                   'Entity Type': 'Phrase'},
                                  {uid: {'Resolution': 'Notes Word Count', 'Notes': ''}}])

        return return_result
