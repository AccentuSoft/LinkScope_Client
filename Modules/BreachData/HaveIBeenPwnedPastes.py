#!/usr/bin/env python3


class HaveIBeenPwnedPastes:
    name = "HIBP Paste Lookup"
    category = "Leaked Data"
    description = "Find all pastes that an account has been involved in."
    originTypes = {'Email Address'}
    resultTypes = {'Paste Data Leak'}
    parameters = {'HIBP API Key': {'description': 'Enter your "Have I Been Pwned" API key. '
                                                  'You can get a key here: https://haveibeenpwned.com/API/Key',
                                   'type': 'String',
                                   'value': '',
                                   'global': True,
                                   'default': 'None'}}

    def resolution(self, entityJsonList, parameters):
        import requests
        import json
        from time import sleep
        from urllib.parse import quote_plus

        baseURL = "https://haveibeenpwned.com/api/v3/pasteaccount/"
        requestHeaders = {'hibp-api-key': parameters['HIBP API Key'].strip(), 'user-agent': 'LinkScope Client'}

        returnResults = []

        count = 0
        while count < len(entityJsonList):
            entity = entityJsonList[count]
            emailAddress = entity['Email Address']
            pasteInfoRequest = requests.get(baseURL + quote_plus(emailAddress), headers=requestHeaders)
            statusCode = pasteInfoRequest.status_code
            if statusCode == 401:
                return "The HIBP API Key provided is invalid."
            elif statusCode == 429:
                sleep(2)
                continue
            elif statusCode == 503:
                return "The HIBP Service is unavailable."
            elif statusCode == 200:
                pasteContent = json.loads(pasteInfoRequest.content)

                for paste in pasteContent:
                    pasteID = paste['Id']
                    pasteSource = paste['Source']
                    pasteTitle = paste['Title']
                    pasteDate = paste['Date']  # If None, will be the date that this entity was created.
                    pasteEmails = str(paste['EmailCount'])

                    returnResults.append([{'Paste Identifier': pasteSource + ' | ' + pasteID,
                                           'Title': pasteTitle,
                                           'Source': pasteSource,
                                           'Paste ID': pasteID,
                                           'Email Count': pasteEmails,
                                           'Entity Type': 'Paste Data Leak',
                                           'Date Created': pasteDate},
                                          {entity['uid']: {'Resolution': 'Contained in Paste',
                                                           'Notes': ''}}])
            sleep(1.7)
            count += 1
        return returnResults
