#!/usr/bin/env python3


class HunterDomainEmailSearch:
    name = "Hunter.io Domain Email Search"
    description = "Find all the emails associated with a domain"
    originTypes = {"Domain"}
    resultTypes = {'Email Address'}
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
                crafted_url = f"{url}domain-search?domain={primary_field}&api_key={api_key}"
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
            for email in response['data']['emails']:
                return_result.append([{'Email Address': email['value'],
                                       'Entity Type': 'Email Address'},
                                      {uid: {'Resolution': 'Hunter.io Domain Search', 'Notes': ''}}])
        return return_result
