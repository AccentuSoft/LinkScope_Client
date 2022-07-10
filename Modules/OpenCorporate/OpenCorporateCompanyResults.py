#!/usr/bin/env python3


class OpenCorporateCompanyResults:
    name = "OpenCorporates Company Lookup"

    category = "OpenCorporates"

    description = "Look up Companies in the OpenCorporates data set."

    originTypes = {'Phrase', 'Company', 'Open Corporates Company'}

    resultTypes = {'Open Corporates Company'}

    parameters = {'Max Results': {'description': 'Please enter the maximum number of results to return.',
                                  'type': 'String',
                                  'value': ''},

                  'Inactive Companies': {'description': 'Display Inactive Companies',
                                         'type': 'SingleChoice',
                                         'value': {'Yes', 'No'}
                                         },
                  'OpenCorporates API Key': {
                      'description': 'Enter your API Key. If you do not have one, type: No Key (case sensitive).\n'
                                     'Standard Free API limits: 50 requests per day, 5 requests per second.\n'
                                     'If you exceed the limits, no results will be returned.\n'
                                     'For more information on API premium plans visit:\n'
                                     'https://opencorporates.com/api_accounts/new',
                      'type': 'String',
                      'value': '',
                      'global': True}
                  }

    def resolution(self, entityJsonList, parameters):
        import requests
        import time
        from urllib import parse
        returnResults = []
        officer_url = 'https://api.opencorporates.com/v0.4/companies/search'
        try:
            maxResults = int(parameters['Max Results'])
        except ValueError:
            return "Invalid integer provided in 'Max Results' parameter"
        if maxResults <= 0:
            return []

        for entity in entityJsonList:
            uid = entity['uid']

            if parameters['OpenCorporates API Key'] == 'No Key':
                # Set up parameters
                data_params = parse.urlencode({
                    'q': entity[list(entity)[1]]
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
                    'q': entity[list(entity)[1]],
                    'api_token': parameters['OpenCorporates API Key']
                })
                try:
                    r = requests.get(
                        url=officer_url,
                        params=data_params,
                        timeout=80,  # High timeouts as they can sometimes take a while
                    )
                except requests.exceptions.ConnectionError:
                    return "Please check your internet connection"
                # Rate limited to the Starter API rate.
                time.sleep(0.02)
                data = r.json

            if r.status_code == 401:
                return 'Invalid API Key'

            elif r.status_code == 403:
                return 'API Limit Reached'

            openCorporatesResults = data['results']['companies'][:maxResults]

            if parameters['Inactive Companies'] == 'Yes':
                for result in openCorporatesResults:
                    returnResults.append([{'Company Name': result['company']['name'],
                                           'Company Number': result['company']['company_number'],
                                           'Jurisdiction Code': result['company'][
                                               'jurisdiction_code'],
                                           'Current Status': result['company']['current_status'],
                                           'Incorporation Date': result['company'][
                                               'incorporation_date'],
                                           'Dissolution Date': result['company']['dissolution_date'],
                                           'Company Type': result['company']['company_type'],
                                           'Registry URL': result['company']['registry_url'],
                                           'Entity Type': 'Open Corporates Company'},
                                          {uid: {'Resolution': 'OpenCorporates Company Resolution', 'Notes': ''}}])

            elif parameters['Inactive Companies'] == 'No':
                for result in openCorporatesResults:
                    if not result['company']['inactive']:
                        returnResults.append([{'Company Name': result['company']['name'],
                                               'Company Number': result['company']['company_number'],
                                               'Jurisdiction Code': result['company'][
                                                   'jurisdiction_code'],
                                               'Current Status': result['company']['current_status'],
                                               'Incorporation Date': result['company'][
                                                   'incorporation_date'],
                                               'Dissolution Date': result['company'][
                                                   'dissolution_date'],
                                               'Company Type': result['company']['company_type'],
                                               'Registry URL': result['company']['registry_url'],
                                               'Entity Type': 'Open Corporates Company'},
                                              {uid: {'Resolution': 'OpenCorporates Company Resolution', 'Notes': ''}}])

        return returnResults
