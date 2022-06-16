#!/usr/bin/env python3


class HaveIBeenPwnedPassword:
    name = "HIBP Password Lookup"
    category = "Leaked Data"
    description = "Check whether the given password was found in breaches."
    originTypes = {'Phrase'}
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
        from hashlib import sha1

        baseURL = "https://api.pwnedpasswords.com/range/"
        requestHeaders = {'hibp-api-key': parameters['HIBP API Key'].strip(), 'user-agent': 'LinkScope Client'}

        returnResults = []

        count = 0
        while count < len(entityJsonList):
            entity = entityJsonList[count]

            primaryField = sha1(entity[list(entity)[1]].encode('utf-8')).hexdigest().upper()
            hashPrefix = primaryField[:5]
            hashSuffix = primaryField[5:]

            breachInfoRequest = requests.get(baseURL + hashPrefix, headers=requestHeaders)
            statusCode = breachInfoRequest.status_code
            if statusCode == 401:
                return "The HIBP API Key provided is invalid."
            elif statusCode == 429:
                sleep(2)
                continue
            elif statusCode == 503:
                return "The HIBP Service is unavailable."
            elif statusCode == 200:
                pwnedPasswordContent = breachInfoRequest.content.decode('utf-8').split('\r\n')

                for password in pwnedPasswordContent:
                    if hashSuffix in password:
                        returnResults.append([{'Phrase': 'Password Hash Found ' + password.split(':')[1] +
                                                         ' times in breach data.',
                                               'Entity Type': 'Phrase'},
                                              {entity['uid']: {'Resolution': 'Pwned Password',
                                                               'Notes': ''}}])
                        break
            sleep(1.7)
            count += 1
        return returnResults
