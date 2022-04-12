#!/usr/bin/env python3


class EmailToDomain:
    name = "Email To Domain"
    category = "Network Infrastructure"
    description = "Get the Domain that an email address belongs to."
    originTypes = {'Email Address'}
    resultTypes = {'Domain'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):

        returnResults = []

        for entity in entityJsonList:
            primaryField = entity['Email Address']
            # There is no provider that I am aware of that allows '@' signs in the user part of the email.
            try:
                returnResults.append([{'Domain Name': primaryField.split('@')[1].strip(),
                                       'Entity Type': 'Domain'},
                                      {entity['uid']: {'Resolution': 'Email To Domain',
                                                       'Notes': ''}}])
            except Exception:
                pass

        return returnResults
