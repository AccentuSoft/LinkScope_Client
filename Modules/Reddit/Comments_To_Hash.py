#!/usr/bin/env python3


class Comments_To_Hash:
    name = "Comments To Hash"
    description = "Transform a Reddit Comment entity to a Hash entity."
    originTypes = {'Reddit Comment'}
    resultTypes = {'Hash'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        return_result = []
        for entity in entityJsonList:
            uid = entity['uid']
            primary_field = entity[list(entity)[1]].strip()
            comment = entity['Notes']
            return_result.append([{'Hash Value': primary_field,
                                   'Hash Algorithm': 'MD5',
                                   'Notes': comment,
                                   'Entity Type': 'Hash'},
                                  {uid: {'Resolution': 'Reddit Comment Hash', 'Notes': ''}}])
        return return_result
