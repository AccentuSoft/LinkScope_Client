#!/usr/bin/env python3


class HunterEmailVerifier:
    name = "Hunter.io Email Verifier"
    description = "Verify an email using hunter.io"
    originTypes = {"Email Address"}
    resultTypes = {'Phrase'}
    parameters = {'Hunter API Key': {'description': "Enter the api key under your profile after signing up at "
                                                    "https://hunter.io/",
                                     'type': 'String',
                                     'value': '',
                                     'global': True}}

    def resolution(self, entityJsonList, parameters):
        import requests
        from requests_futures.sessions import FuturesSession
        from concurrent.futures import as_completed

        return_result = []
        futures = []
        uidList = []

        api_key = parameters['Hunter API Key']
        url = "https://api.hunter.io/v2/"

        with FuturesSession(max_workers=15) as session:
            for entity in entityJsonList:
                uidList.append(entity['uid'])
                primary_field = entity[list(entity)[1]]
                crafted_url = f"{url}email-verifier?email={primary_field}&api_key={api_key}"
                futures.append(session.get(crafted_url))
        response = {}
        for future in as_completed(futures):
            uid = uidList[futures.index(future)]
            try:
                if future.result().status_code == 401:
                    return "The API Key provided is Invalid"
                elif future.result().status_code == 200:
                    response = future.result().json()
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"
            return_result.append([{'Phrase': f"The email {primary_field} is {response['data']['status']}",
                                   'Entity Type': 'Phrase'},
                                  {uid: {'Resolution': 'Hunter.io Email Verifier', 'Notes': ''}}])
        return return_result
