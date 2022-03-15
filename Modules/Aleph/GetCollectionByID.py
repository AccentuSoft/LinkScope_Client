#!/usr/bin/env python3


class GetCollectionByID:
    name = "Get Collections By ID"
    category = "Aleph OCCRP"
    description = "Find information about Collections and their IDs"
    originTypes = {'Phrase'}
    resultTypes = {'Phrase. Person, Address, Phone Number, Email Address, Country, Bank Account'}
    parameters = {'Aleph Disclaimer': {'description': 'The content on Aleph is provided for general information only.\n'
                                                      'It is not intended to amount to advice on which you should place'
                                                      'sole and entire reliance.\n'
                                                      'We recommend that you conduct your own independent fact checking'
                                                      'against the data and materials that you access on Aleph.\n'
                                                      'Aleph API is not a replacement for traditional due diligence '
                                                      'checks and know-your-customer background checks.',
                                       'type': 'String',
                                       'value': 'Type "Accept" (without quotes) to confirm your understanding.',
                                       'global': True}}

    def resolution(self, entityJsonList, parameters):
        import time
        import requests
        from requests_futures.sessions import FuturesSession
        from concurrent.futures import as_completed

        returnResults = []
        futures = []
        uidList = []

        if parameters['Aleph Disclaimer'] != 'Accept':
            return "Please Accept the Terms for Aleph."

        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        with FuturesSession(max_workers=15) as session:
            for entity in entityJsonList:
                uidList.append(entity['uid'])
                primary_field = entity[list(entity)[1]].strip()
                url = f"https://aleph.occrp.org/api/2/collections/{primary_field}"
                time.sleep(1)
                futures.append(session.get(url, headers=headers))
        for future in as_completed(futures):
            uid = uidList[futures.index(future)]
            try:
                response = future.result().json()
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"
            if response['statistics']['names'].get('values') is not None:
                nameKeys = list(response['statistics']['names'].get('values').keys())
                for nameKey in nameKeys:
                    returnResults.append([{'Full Name': str(nameKey),
                                           'Entity Type': 'Person'},
                                          {uid: {'Resolution': 'Person Entity',
                                                 'Notes': ''}}])
            if response['statistics']['addresses'].get('values') is not None:
                addressKeys = list(response['statistics']['addresses'].get('values').keys())
                for addressKey in addressKeys:
                    returnResults.append([{'Street Address': str(addressKey),
                                           'Entity Type': 'Address'},
                                          {uid: {'Resolution': 'Address Entity',
                                                 'Notes': ''}}])
            if response['statistics']['phones'].get('values') is not None:
                phoneKeys = list(response['statistics']['phones'].get('values').keys())
                for phoneKey in phoneKeys:
                    returnResults.append([{'Phone Number': str(phoneKey),
                                           'Entity Type': 'Phone Number'},
                                          {uid: {'Resolution': 'Phone Number Entity',
                                                 'Notes': ''}}])

            if response['statistics']['emails'].get('values') is not None:
                emailKeys = list(response['statistics']['emails'].get('values').keys())
                for emailKey in emailKeys:
                    returnResults.append([{'Email Address': str(emailKey),
                                           'Entity Type': 'Email Address'},
                                          {uid: {'Resolution': 'Email Address Entity',
                                                 'Notes': ''}}])
            if response['statistics']['countries'].get('values') is not None:
                countriesKeys = list(response['statistics']['countries'].get('values').keys())
                for countriesKey in countriesKeys:
                    returnResults.append([{'Country Name': str(countriesKey),
                                           'Entity Type': 'Country'},
                                          {uid: {'Resolution': 'Country Entity',
                                                 'Notes': ''}}])
            if response['statistics']['languages'].get('values') is not None:
                languagesKeys = list(response['statistics']['languages'].get('values').keys())
                for languagesKey in languagesKeys:
                    returnResults.append([{'Phrase': str(languagesKey),
                                           'Entity Type': 'Phrase'},
                                          {uid: {'Resolution': 'Language Entity',
                                                 'Notes': ''}}])
            if response['statistics']['ibans'].get('values') is not None:
                ibansKeys = list(response['statistics']['ibans'].get('values').keys())
                for ibansKey in ibansKeys:
                    returnResults.append([{'Account Number': str(ibansKey),
                                           'Entity Type': 'Bank Account'},
                                          {uid: {'Resolution': 'IBAN Entity',
                                                 'Notes': ''}}])
        return returnResults
