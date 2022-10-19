#!/usr/bin/env python3


class OpenCorporateCompaniesAddress:
    name = "Get OpenCorporates Company's Address"

    category = "OpenCorporates"

    description = "Returns the Address of an OpenCorporates Company."

    originTypes = {'Open Corporates Company'}

    resultTypes = {'Address'}

    parameters = {'Max Results': {'description': 'Please enter the maximum number of results to return.',
                                  'type': 'String',
                                  'value': '',
                                  'default': '5'},

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

        company_url = 'https://api.opencorporates.com/v0.4/companies/search'
        try:
            maxResults = int(parameters['Max Results'])
        except ValueError:
            return "Invalid integer provided in 'Max Results' parameter"
        if maxResults <= 0:
            return []

        for entity in entityJsonList:
            uid = entity['uid']

            if parameters['OpenCorporates API Key'].strip() == 'No Key':
                # Set up parameters
                data_params = parse.urlencode({
                    'q': entity['Company Name']
                })
                # Perform and process get request
                try:
                    r = requests.get(url=company_url, params=data_params)
                except requests.exceptions.ConnectionError:
                    return "Please check your internet connection"
                time.sleep(0.25)

                data = r.json()
            else:
                data_params = parse.urlencode({
                    'q': entity['Company Name'],
                    'api_token': parameters['API Key']
                })
                r = requests.get(
                    url=company_url,
                    params=data_params,
                    timeout=80,  # High timeouts as they can sometimes take a while
                )
                # Rate limited to the Starter API rate.
                time.sleep(0.02)
                data = r.json()

            if r.status_code == 401:
                return 'Invalid API Key'

            elif r.status_code == 403:
                return 'API Limit Reached'

            try:
                openCorporatesResults = data['results']['companies'][:maxResults]
            except KeyError:
                continue

            for result in openCorporatesResults:
                if result['company']['registered_address'] is None:
                    continue
                else:
                    returnResult.append(
                        [{'Street Address': result['company']['registered_address']['street_address'],
                          'Locality': result['company']['registered_address']['locality'],
                          'Postal Code': result['company']['registered_address']['postal_code'],
                          'Country': result['company']['registered_address']['country'],
                          'Entity Type': 'Address'},
                         {uid: {'Resolution': 'Company Location', 'Notes': ''}}])

        return returnResult
