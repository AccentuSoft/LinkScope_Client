#!/usr/bin/env python3


class EvaPingUtil:
    name = "Eva PingUtil Email Check"
    category = "Reputation Check"
    description = "Check if an email address is disposable, spam, or gibberish."
    originTypes = {'Email Address', 'Domain'}
    resultTypes = {'Phrase'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import requests

        returnResults = []

        for entity in entityJsonList:
            entityType = entity['Entity Type']
            if entityType == 'Email Address':
                email = entity['Email Address']
            elif entityType == 'Domain':
                email = f"{entity['Domain Name'].split('.')[0]}@{entity['Domain Name']}"
            else:
                continue
            result = requests.get('https://api.eva.pingutil.com/email?email=' + email).json()
            disposable = result['data']['disposable']
            spam = result['data']['spam']
            gibberish = result['data']['gibberish']
            if disposable or spam or gibberish:
                returnResults.append([{'Phrase': 'Poor Reputation: ' + email,
                                       'Disposable': str(disposable),
                                       'Spam': str(spam),
                                       'Gibberish': str(gibberish),
                                       'Entity Type': 'Phrase'},
                                      {entity['uid']: {'Resolution': 'Eva PingUtil Email Check',
                                                       'Notes': ''}}])
            else:
                returnResults.append([{'Phrase': 'Good Reputation: ' + email,
                                       'Disposable': str(disposable),
                                       'Spam': str(spam),
                                       'Gibberish': str(gibberish),
                                       'Entity Type': 'Phrase'},
                                      {entity['uid']: {'Resolution': 'Eva PingUtil Email Check',
                                                       'Notes': ''}}])

        return returnResults
