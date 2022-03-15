#!/usr/bin/env python3


class SpyOnWeb:
    name = "SpyOnWeb API"

    category = "Website Information"

    description = "Discover Websites Connections through UA numbers"

    originTypes = {'Domain'}

    resultTypes = {'Domain , Phrase'}

    parameters = {'Max UAs to Scan': {'description': 'Please enter the maximum number of UA Numbers to scan and '
                                                     'return. Enter "0" (no quotes) to return all available results.',
                                      'type': 'String',
                                      'default': '0'},

                  'Max Results': {'description': 'Please enter the maximum number of domains to return. '
                                                 'Enter "0" (no quotes) to return all available results.',
                                  'type': 'String',
                                  'default': '0'},

                  'SpyOnWeb API Key': {'description': 'Enter your API Key. API Key is necessary. '
                                                      'Standard Free API limits: 200 requests per month, 10,000 '
                                                      'summary requests per month. If you exceed the limits or '
                                                      'provide bad API keys, no results will be returned. '
                                                      'For more information on API premium plans visit: '
                                                      'https://api.spyonweb.com/account/upgrade',
                                       'type': 'String',
                                       'value': '',
                                       'global': True
                                       }
                  }

    def resolution(self, entityJsonList, parameters):
        import requests
        returnResults = []
        keys = []
        try:
            linkNumbers = int(parameters['Max Results'])
            uaNumber = int(parameters['Max UAs to Scan'])
        except ValueError:
            return "Non-integers provided in parameters which expected integers; resolution cannot run."
        if linkNumbers == 0:
            linkNumbers = 9999999999
        if uaNumber == 0:
            uaNumber = 9999999999
        if linkNumbers < 0 or uaNumber < 0:
            return []

        api_token = parameters['SpyOnWeb API Key'].strip()

        for entity in entityJsonList:
            uid = entity['uid']

            domain = entity[list(entity)[1]]
            try:
                request = requests.get(f'https://api.spyonweb.com/v1/summary/{domain}?access_token={api_token}')
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"
            # Rate limited to the Starter API rate.
            data = request.json()

            if request.status_code == 401:
                return 'Incorrect API Key'

            elif request.status_code == 403:
                if len(returnResults) > 0:
                    return returnResults
                return 'API Limit Reached'

            try:
                uaData = data['result']['summary'][domain]['items']['analytics'].keys()
            except KeyError:
                continue

            ua_tokens = list(uaData)

            # loops need to be nested to connect corresponding keys to the UA
            for tracking_token in ua_tokens:
                request = requests.get(f'https://api.spyonweb.com/v1/analytics/'
                                       f'{tracking_token}?access_token={api_token}')
                # Rate limited to the Starter API rate.
                dataDomain = request.json()
                if request.status_code == 401 or request.status_code == 403:
                    continue

                if uaNumber >= len(ua_tokens):
                    uaNumber = int(len(ua_tokens))

                index_of_child = len(returnResults)
                returnResults.append([{'Phrase': tracking_token,
                                       'Entity Type': 'Phrase'},
                                      {uid: {'Resolution': 'UA Number',
                                             'Notes': ''}}])

                if dataDomain['status'] == 'found':
                    for key in dataDomain['result']['analytics'][tracking_token]['items'].keys():
                        keys.append(key)

                if linkNumbers >= len(keys):
                    linkNumbers = int(len(keys))

                for j in range(linkNumbers):
                    returnResults.append([{'Domain Name': keys[j],
                                           'Entity Type': 'Domain'},
                                          {index_of_child: {'Resolution': 'Domain',
                                                            'Notes': ''}}])

            for tracking_token in data['result']['summary'][domain]['items']['dns_servers'].keys():
                returnResults.append([{'Phrase': tracking_token,
                                       'Entity Type': 'Phrase'},
                                      {uid: {'Resolution': 'DNS server',
                                             'Notes': ''}}])

        return returnResults
