#!/usr/bin/env python3


class HunterPersonEmailFinder:
    name = "Hunter.io Person Email Finder"
    description = "Find the email of a person by scanning a domain with hunter.io and providing a Full Name"
    originTypes = {"Domain"}
    resultTypes = {'Email Address'}
    parameters = {'Hunter API Key': {'description': "Enter the api key under your profile after signing up at "
                                                    "https://hunter.io/",
                                     'type': 'String',
                                     'value': '',
                                     'global': True},
                  'Full Name': {'description': "Enter the Full Name with space in between (John Doe)",
                                'type': 'String',
                                'value': ''}}

    def resolution(self, entityJsonList, parameters):
        import requests
        from requests_futures.sessions import FuturesSession
        from concurrent.futures import as_completed

        return_result = []
        futures = []
        uidList = []

        api_key = parameters['Hunter API Key']
        try:
            first, last = parameters['Full Name'].strip().split(" ")
        except ValueError:
            return "Please enter only a first and last name. It has to be only two words with a space in between."

        url = "https://api.hunter.io/v2/"
        with FuturesSession(max_workers=15) as session:
            for entity in entityJsonList:
                uidList.append(entity['uid'])
                primary_field = entity[list(entity)[1]]
                crafted_url = \
                    f"{url}email-finder?domain={primary_field}&first_name={first}&last_name={last}&api_key={api_key}"
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
            return_result.append([{'Email Address': response['data']['email'],
                                   'Entity Type': 'Email Address'},
                                  {uid: {'Resolution': 'Hunter.io Person Email Finder', 'Notes': ''}}])
        return return_result
