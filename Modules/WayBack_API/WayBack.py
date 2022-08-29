#!/usr/bin/env python3


class WayBack:
    # A string that is treated as the name of this resolution.
    name = "Get WayBack Pages"

    category = "Website Information"

    # A string that describes this resolution.
    description = "Returns Nodes of websites for the requested time period"

    originTypes = {'Website', 'Domain'}

    resultTypes = {'Website'}

    parameters = {'Max Results': {'description': 'Please enter the maximum number of webpages to return.',
                                  'type': 'String',
                                  'value': 'Maximum number of results',
                                  'default': '5'},
                  'Year range to search for': {'description': 'Please enter the range of years desired\n'
                                                              'In the Format: [start year] [end year]\n',
                                               'type': 'String',
                                               'value': "E.g.: '2000 2010' (no quotes)"}
                  }

    def resolution(self, entityJsonList, parameters):
        import requests
        from requests_futures.sessions import FuturesSession
        from concurrent.futures import as_completed

        returnResults = []
        futures = []
        uidList = []

        try:
            max_results = int(parameters['Max Results'])
        except ValueError:
            return "The value for parameter 'Max Results' is not a valid integer."
        if max_results <= 0:
            return []
        yearRange = parameters['Year range to search for'].split(" ")

        with FuturesSession(max_workers=15) as session:
            for entity in entityJsonList:
                uidList.append(entity['uid'])
                primary_field = entity[list(entity)[1]]
                futures.append(session.get(
                    f'http://web.archive.org/cdx/search/cdx?url={primary_field}&from={yearRange[0]}&to={yearRange[1]}'
                    f'&output=json&limit={max_results}'))
            for future in as_completed(futures):
                uid = uidList[futures.index(future)]
                try:
                    response = future.result().json()
                except requests.exceptions.ConnectionError:
                    return "Please check your internet connection"
                # 4 = status code, 1 = timestamp, 2 = original
                response = response[1:]
                for value in response:
                    if value[4] == '200':
                        returnResults.append(
                            [{'URL': "http://web.archive.org/web/" + str(value[1]) + '/' + str(value[2]),
                              'Entity Type': 'Website'},
                             {uid: {'Resolution': 'Older Version',
                                    'Notes': str(value[5])}}])

        return returnResults
