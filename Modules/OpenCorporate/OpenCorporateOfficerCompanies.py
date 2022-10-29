#!/usr/bin/env python3


class OpenCorporateOfficerCompanies:
    name = "Get OpenCorporates Officer's Companies"

    category = "OpenCorporates"

    description = "Returns Nodes of Companies where the Person is an Officer."

    originTypes = {'Person', 'Phrase', 'Open Corporates Officer'}

    resultTypes = {'Company'}

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
        officer_url = 'https://api.opencorporates.com/v0.4/officers/search'
        try:
            maxResults = int(parameters['Max Results'])
        except ValueError:
            return "Invalid integer provided in 'Max Results' parameter"
        if maxResults <= 0:
            return []

        for entity in entityJsonList:
            uid = entity['uid']
            primaryField = entity[list(entity)[1]]
            if entity['Entity Type'] == 'Open Corporates Officer':
                primaryField = primaryField.split(' | ')[0]  # Nobody has ' | ' in their name - 2022/7/10

            if parameters['OpenCorporates API Key'].strip() == 'No Key':
                # Set up parameters
                data_params = parse.urlencode({
                    'q': primaryField
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
                    'q': primaryField,
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
                # print(r)
                data = r.json()

            if r.status_code == 401:
                return 'Invalid API Key'

            elif r.status_code == 403:
                return 'API Limit Reached'

            openCorporateResults = data['results']['officers'][:maxResults]

            if parameters['Inactive Companies'] == 'Yes':
                for result in openCorporateResults:
                    occupation = result['officer']['occupation']
                    returnResults.append(
                        [{'Company Name': result['officer']['company']['name'],
                          'Registration Number': result['officer']['company']['company_number'],
                          'Jurisdiction Code': result['officer']['company']['jurisdiction_code'],
                          'OpenCorporates URL': result['officer']['company']['opencorporates_url'],
                          'Entity Type': 'Company'},
                         {uid: {'Resolution': occupation if occupation else 'Unknown Position in Company',
                                'Notes': ''}}])

            elif parameters['Inactive Companies'] == 'No':
                for result in openCorporateResults:
                    if not result['officer']['inactive']:
                        occupation = result['officer']['occupation']
                        returnResults.append(
                            [{'Company Name': result['officer']['company']['name'],
                              'Registration Number': result['officer']['company']['company_number'],
                              'Jurisdiction Code': result['officer']['company']['jurisdiction_code'],
                              'OpenCorporates URL': result['officer']['company']['opencorporates_url'],
                              'Entity Type': 'Company'},
                             {uid: {'Resolution': occupation if occupation else 'Unknown Position in Company',
                                    'Notes': ''}}])
        return returnResults
