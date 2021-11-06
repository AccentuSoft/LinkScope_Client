#!/usr/bin/env python3


class OpenCorporateCompanyResults:
    name = "OpenCorporate Company Lookup"

    description = "Returns Results per Company"

    originTypes = {'Phrase', 'Company', 'Open Corporate Company'}

    resultTypes = {'Open Corporate Company'}

    parameters = {'Max Results': {'description': 'Please enter the maximum number of results to return. '
                                                 'Enter "0" (no quotes) to return all available results.',
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
        linkNumbers = int(parameters['Max Results'])
        if linkNumbers == 0:
            linkNumbers = 9999999999

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

            openCorporatesResults = data['results']['companies']

            if linkNumbers >= len(openCorporatesResults):
                linkNumbers = int(len(openCorporatesResults))

            if parameters['Inactive Companies'] == 'Yes':
                for i in range(linkNumbers):
                    returnResults.append([{'Company Name': openCorporatesResults[i]['company']['name'],
                                           'Company Number': openCorporatesResults[i]['company']['company_number'],
                                           'Jurisdiction Code': openCorporatesResults[i]['company'][
                                               'jurisdiction_code'],
                                           'Current Status': openCorporatesResults[i]['company']['current_status'],
                                           'Incorporation Date': openCorporatesResults[i]['company'][
                                               'incorporation_date'],
                                           'Dissolution Date': openCorporatesResults[i]['company']['dissolution_date'],
                                           'Company Type': openCorporatesResults[i]['company']['company_type'],
                                           'Registry URL': openCorporatesResults[i]['company']['registry_url'],
                                           'Entity Type': 'Open Corporate Company'},
                                          {uid: {'Resolution': 'OpenCorpRes', 'Notes': ''}}])

            elif parameters['Inactive Companies'] == 'No':
                for i in range(linkNumbers):
                    if not openCorporatesResults[i]['company']['inactive']:
                        returnResults.append([{'Company Name': openCorporatesResults[i]['company']['name'],
                                               'Company Number': openCorporatesResults[i]['company']['company_number'],
                                               'Jurisdiction Code': openCorporatesResults[i]['company'][
                                                   'jurisdiction_code'],
                                               'Current Status': openCorporatesResults[i]['company']['current_status'],
                                               'Incorporation Date': openCorporatesResults[i]['company'][
                                                   'incorporation_date'],
                                               'Dissolution Date': openCorporatesResults[i]['company'][
                                                   'dissolution_date'],
                                               'Company Type': openCorporatesResults[i]['company']['company_type'],
                                               'Registry URL': openCorporatesResults[i]['company']['registry_url'],
                                               'Entity Type': 'Open Corporate Company'},
                                              {uid: {'Resolution': 'OpenCorpRes', 'Notes': ''}}])

        return returnResults
