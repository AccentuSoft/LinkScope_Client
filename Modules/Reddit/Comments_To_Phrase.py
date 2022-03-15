#!/usr/bin/env python3


class Comments_To_Phrase:
    name = "Comments To Phrase"
    category = "Reddit"
    description = "Transform a Reddit Comment entity to a Phrase entity."
    originTypes = {'Reddit Comment'}
    resultTypes = {'Phrase'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        return_result = []
        for entity in entityJsonList:
            uid = entity['uid']
            primary_field = entity[list(entity)[1]].strip()
            comment = entity['Notes']
            return_result.append([{'Phrase': primary_field,
                                   'Notes': comment,
                                   'Entity Type': 'Phrase'},
                                  {uid: {'Resolution': 'Reddit Comment Phrase', 'Notes': ''}}])
        return return_result
