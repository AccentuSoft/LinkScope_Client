#!/usr/bin/env python3


class OpenCorporateCompaniesAddress:
    name = "Get OpenCorporate Company's Address"

    description = "Returns Address per company."

    originTypes = {'Phrase', 'Company', 'Open Corporate Company'}

    resultTypes = {'Address'}

    parameters = {'Max Results': {'description': 'Please enter the maximum number of results to return. '
                                                 'Enter "0" (no quotes) to return all available results.',
                                  'type': 'String',
                                  'value': ''},

                  'OpenCorporates API Key': {
                      'description': 'Enter your API Key. If you do not have one, type: No Key (case sensitive).\n'
                                     'Standard Free API limits: 50 requests per day, 5 requests per second.\n'
                                     'If you exceed the limits, no results will be returned.\n'
                                     'For more information on API premium plans visit:\n'
                                     'https://opencorporates.com/api_accounts/new',
                      'type': 'String',
                      'default': 'No Key',
                      'global': True}
                  }

    def resolution(self, entityJsonList, parameters):
        import requests
        import time
        from urllib import parse
        returnResult = []

        officer_url = 'https://api.opencorporates.com/v0.4/companies/search'
        linkNumbers = int(parameters['Max Results'])
        if linkNumbers == 0:
            linkNumbers = 9999999999

        for entity in entityJsonList:
            uid = entity['uid']

            if parameters['OpenCorporates API Key'] == 'No Key':
                # Set up parameters
                data_params = parse.urlencode({
                    'q': entity[list(entity)[2]]
                })
                # Perform and process get request
                try:
                    r = requests.get(url=officer_url, params=data_params)
                except requests.exceptions.ConnectionError:
                    return "Please check your internet connection"
                time.sleep(0.25)

                data = r.json()
            else:
                data_params = parse.urlencode({
                    'q': entity[list(entity)[2]],
                    'api_token': parameters['API Key']
                })
                r = requests.get(
                    url=officer_url,
                    params=data_params,
                    timeout=80,  # High timeouts as they can sometimes take a while
                )
                # Rate limited to the Starter API rate.
                time.sleep(0.02)
                data = r.json

            if r.status_code == 401:
                return 'Invalid API Key'

            elif r.status_code == 403:
                return 'API Limit Reached'

            openCorporatesResults = data['results']['companies']
            if linkNumbers >= len(openCorporatesResults):
                linkNumbers = int(len(openCorporatesResults))

            for j in range(linkNumbers):
                if data['results']['companies'][j]['company']['registered_address'] is None:
                    continue
                else:
                    returnResult.append(
                        [{'Street Address': openCorporatesResults[j]['company']['registered_address']['street_address'],
                          'Locality': openCorporatesResults[j]['company']['registered_address']['locality'],
                          'Postal Code': openCorporatesResults[j]['company']['registered_address']['postal_code'],
                          'Country': openCorporatesResults[j]['company']['registered_address']['country'],
                          'Entity Type': 'Address'},
                         {uid: {'Resolution': 'Location', 'Notes': ''}}])

        return returnResult
