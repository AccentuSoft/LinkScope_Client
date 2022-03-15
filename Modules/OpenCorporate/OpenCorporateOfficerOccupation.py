#!/usr/bin/env python3


class OpenCorporateOfficerOccupation:
    name = "Get OpenCorporate Officers"

    category = "OpenCorporates"

    description = "Returns Nodes of Companies where the Person is an Officer"

    originTypes = {'Person', 'Phrase'}

    resultTypes = {'Company'}

    parameters = {'Max Results': {'description': 'Please enter the maximum number of results to return.',
                                  'type': 'String',
                                  'value': ''},

                  'Inactive Officers': {'description': 'Display Inactive Officers',
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
            linkNumbers = int(parameters['Max Results'])
        except ValueError:
            return "Invalid integer provided in 'Max Results' parameter"
        if linkNumbers <= 0:
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
                # print(r)
                data = r.json

            if r.status_code == 401:
                return 'Invalid API Key'

            elif r.status_code == 403:
                return 'API Limit Reached'

            openCorporateResults = data['results']['officers']

            if linkNumbers >= len(openCorporateResults):
                linkNumbers = int(len(openCorporateResults))

            if parameters['Inactive Officers'] == 'Yes':
                for i in range(linkNumbers):
                    returnResults.append([{'Company Name': openCorporateResults[i]['officer']['company']['name'],
                                           'Entity Type': 'Company'},
                                          {uid: {'Resolution': openCorporateResults[i]['officer']['occupation'],
                                                 'Notes': ''}}])

            elif parameters['Inactive Officers'] == 'No':
                for i in range(linkNumbers):
                    if not data['results']['officers'][i]['officer']['inactive']:
                        returnResults.append(
                            [{'Company Name': openCorporateResults[i]['officer']['company']['name'],
                              'Entity Type': 'Company'},
                             {uid: {'Resolution': openCorporateResults[i]['officer']['occupation'],
                                    'Notes': ''}}])
        return returnResults
