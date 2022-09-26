#!/usr/bin/env python3


class HaveIBeenPwnedBreaches:
    name = "HIBP Breach Lookup"
    category = "Leaked Data"
    description = "Find all breaches that an account has been involved in. Note that Date Created for breaches is an " \
                  "estimate."
    originTypes = {'Email Address', 'Phone Number'}
    resultTypes = {'Data Breach'}
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

        from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QSize
        from PySide6.QtGui import QImage

        baseURL = "https://haveibeenpwned.com/api/v3/breachedaccount/"
        requestHeaders = {'hibp-api-key': parameters['HIBP API Key'].strip(), 'user-agent': 'LinkScope Client'}

        returnResults = []

        count = 0
        while count < len(entityJsonList):
            entity = entityJsonList[count]
            primaryField = entity[list(entity)[1]]
            breachInfoRequest = requests.get(baseURL + quote_plus(primaryField) + '?truncateResponse=false',
                                             headers=requestHeaders)
            statusCode = breachInfoRequest.status_code
            if statusCode == 200:
                breachContent = json.loads(breachInfoRequest.content)

                for breach in breachContent:
                    try:
                        breachLogoIconRequest = requests.get(breach['LogoPath'])
                        breachIconByteArray = QByteArray(breachLogoIconRequest.content)
                        breachIconImageOriginal = QImage().fromData(breachIconByteArray)
                        breachIconImageScaled = breachIconImageOriginal.scaled(QSize(40, 40))

                        # Rotate the breach domain logo upside down
                        breachIconImageRotated = breachIconImageScaled.mirrored()

                        breachIconByteArrayFin = QByteArray()
                        breachImageBuffer = QBuffer(breachIconByteArrayFin)
                        breachImageBuffer.open(QIODevice.WriteOnly)
                        breachIconImageRotated.save(breachImageBuffer, "PNG")
                        breachImageBuffer.close()
                    except Exception:
                        breachIconByteArrayFin = None

                    # If Breach Date is None, then default to entity creation date.
                    returnResults.append([{'Breach Name': breach['Name'],
                                           'Breach Title': breach['Title'],
                                           'Breach Domain': breach['Domain'],
                                           'Breach Pwn Count': str(breach['PwnCount']),
                                           'Breach Description': breach['Description'],
                                           'Breach Is Sensitive': str(breach['IsSensitive']),
                                           'Breach Is Verified': str(breach['IsVerified']),
                                           'Breach Is Fabricated': str(breach['IsFabricated']),
                                           'Breach Is Retired': str(breach['IsRetired']),
                                           'Breach Is Spam List': str(breach['IsSpamList']),
                                           'Breach Is Malware': str(breach['IsMalware']),
                                           'Breach Added Date': breach['AddedDate'],
                                           'Breach Modified Date': breach['ModifiedDate'],
                                           'Entity Type': 'Data Breach',
                                           'Icon': breachIconByteArrayFin,  # If None -> Default breach icon.
                                           'Date Created': breach['BreachDate']},
                                          {entity['uid']: {'Resolution': 'Contained in Breach',
                                                           'Notes': ''}}])
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
