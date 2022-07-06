#!/usr/bin/env python3


class KickboxMailDisposable:
    name = "Kickbox Disposable Email Check"
    category = "Reputation Check"
    description = "Check if an email address is from a disposable provider, or if a domain is known for providing " \
                  "disposable email addresses."
    originTypes = {'Email Address', 'Domain'}
    resultTypes = {'Phrase'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import requests

        returnResults = []

        for entity in entityJsonList:
            entityType = entity['Entity Type']
            if entityType == 'Email Address':
                emailDomain = entity['Email Address'][::-1].split('@', 1)[0][::-1]
            elif entityType == 'Domain':
                emailDomain = entity['Domain Name']
            else:
                continue
            mailDisposable = requests.get('https://open.kickbox.com/v1/disposable/' + emailDomain).json()['disposable']
            if mailDisposable:
                returnResults.append([{'Phrase': 'Disposable: ' + emailDomain,
                                       'Entity Type': 'Phrase'},
                                      {entity['uid']: {'Resolution': 'Kickbox Disposable Email Check',
                                                       'Notes': ''}}])
            else:
                returnResults.append([{'Phrase': 'Not Disposable: ' + emailDomain,
                                       'Entity Type': 'Phrase'},
                                      {entity['uid']: {'Resolution': 'Kickbox Disposable Email Check',
                                                       'Notes': ''}}])

        return returnResults
