#!/usr/bin/env python3


class IPInfo:
    name = "Get IPInfo Results For IP"
    category = "Geolocation"
    description = "Find information about the location of a given IP Address"
    originTypes = {'IP Address'}
    resultTypes = {'Geocordinates', 'Organization', 'City'}
    parameters = {'IPInfo Access Token': {'description': 'Enter your access token key under your profile after '
                                                         'signing up on https://ipinfo.io. Free usage of the API is '
                                                         'limited to 50,000 requests per month. '
                                                         'For any requests beyond that limit, no results will be '
                                                         'returned.',
                                          'type': 'String',
                                          'value': '',
                                          'global': True}}

    def resolution(self, entityJsonList, parameters):
        import requests
        from requests_futures.sessions import FuturesSession
        from concurrent.futures import as_completed
        from ipaddress import ip_address

        return_result = []
        futures = []
        uidList = []
        primaryFields = []

        access_token = parameters['IPInfo Access Token'].strip()
        with FuturesSession(max_workers=15) as session:
            for entity in entityJsonList:
                uidList.append(entity['uid'])
                primary_field = entity[list(entity)[1]].strip()
                primaryFields.append(primary_field)
                try:
                    ip_address(primary_field)
                except ValueError:
                    return "The Entity Provided isn't a valid IP Address"
                url = "https://ipinfo.io/" + str(primary_field) + "?token=" + str(access_token)
                futures.append(session.get(url))
        for future in as_completed(futures):
            uid = uidList[futures.index(future)]
            try:
                if future.result().status_code == 429:
                    if len(return_result) != 0:
                        return return_result
                    return "The API Key provided is Invalid or you are sending requests above the rate limit"
                else:
                    response = future.result().json()
                    latitude, longitude = response['loc'].split(",")
                    return_result.append([{'Label': str(primaryFields[futures.index(future)]) + " Location",
                                           'Latitude': latitude,
                                           'Longitude': longitude,
                                           'Entity Type': 'GeoCoordinates'},
                                          {uid: {'Resolution': 'IPInfo IP Geocordinates', 'Notes': ''}}])
                    return_result.append([{'Organization Name': response['org'],
                                           'Entity Type': 'Organization'},
                                          {uid: {'Resolution': 'IPInfo IP Organization', 'Notes': ''}}])
                    return_result.append([{'City Name': response['city'],
                                           'Entity Type': 'City'},
                                          {uid: {'Resolution': 'IPInfo IP City Name', 'Notes': ''}}])
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"
        return return_result
