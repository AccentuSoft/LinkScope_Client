#!/usr/bin/env python3


class HaveIBeenPwnedPasswordHash:
    name = "HIBP Password Hash Lookup"
    category = "Leaked Data"
    description = "Check whether the given password hash was found in breaches."
    originTypes = {'Hash', 'Phrase'}
    resultTypes = {'Phrase'}
    parameters = {'HIBP API Key': {'description': 'Enter your "Have I Been Pwned" API key. '
                                                  'You can get a key here: https://haveibeenpwned.com/API/Key',
                                   'type': 'String',
                                   'value': '',
                                   'global': True,
                                   'default': 'None'}}

    def resolution(self, entityJsonList, parameters):
        import requests
        from time import sleep

        baseURL = "https://api.pwnedpasswords.com/range/"
        requestHeaders = {'hibp-api-key': parameters['HIBP API Key'].strip(), 'user-agent': 'LinkScope Client'}

        returnResults = []

        count = 0
        while count < len(entityJsonList):
            entity = entityJsonList[count]

            primaryField = entity[list(entity)[1]].upper()
            if len(primaryField) != 40:
                continue
            hashPrefix = primaryField[:5]
            hashSuffix = primaryField[5:]

            breachInfoRequest = requests.get(baseURL + hashPrefix, headers=requestHeaders)
            statusCode = breachInfoRequest.status_code
            if statusCode == 200:
                pwnedPasswordContent = breachInfoRequest.content.decode('utf-8').split('\r\n')

                for password in pwnedPasswordContent:
                    if hashSuffix in password:
                        returnResults.append([{'Phrase': f"Password Hash Found {password.split(':')[1]} times "
                                                         f"in breach data.",
                                               'Entity Type': 'Phrase'},
                                              {entity['uid']: {'Resolution': 'Pwned Password',
                                                               'Notes': ''}}])
                        break
            elif statusCode == 401:
                return "The HIBP API Key provided is invalid."
            elif statusCode == 429:
                sleep(2)
                continue
            elif statusCode == 503:
                return "The HIBP Service is unavailable."
            sleep(1.7)
            count += 1
        return returnResults
