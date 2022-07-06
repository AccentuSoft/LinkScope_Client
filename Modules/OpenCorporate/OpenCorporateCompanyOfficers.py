#!/usr/bin/env python3


class OpenCorporateCompanyOfficers:
    name = "OpenCorporate Company Officers Lookup"

    category = "OpenCorporates"

    description = "Returns the Officers of the specified company."

    originTypes = {'Open Corporate Company'}

    resultTypes = {'Person', 'Date'}

    parameters = {'Max Results': {'description': 'Please enter the maximum number of results to return. '
                                                 'Officer data may not be available for some jurisdictions. '
                                                 'If no data is found the resolution will return no results.',
                                  'type': 'String',
                                  'value': '',
                                  'default': '5'},

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
        returnResults = []
        try:
            maxResults = int(parameters['Max Results'])
        except ValueError:
            return "Invalid integer provided in 'Max Results' parameter"
        if maxResults <= 0:
            return []

        considerInactive = parameters['Inactive Companies'] == 'No'

        for entity in entityJsonList:
            jurisdictionCode = entity[list(entity)[3]]
            companyCode = entity[list(entity)[1]]
            uid = entity['uid']

            if parameters['OpenCorporates API Key'] == 'No Key':
                # Perform and process get request
                try:
                    r = requests.get(f"https://api.opencorporates.com/v0.4/companies/{jurisdictionCode}/{companyCode}")
                except requests.exceptions.ConnectionError:
                    return "Please check your internet connection"
                time.sleep(0.25)

                data = r.json()
            else:
                api_token = parameters['OpenCorporates API Key']
                try:
                    r = requests.get(
                        f"https://api.opencorporates.com/v0.4/companies/"
                        f"{jurisdictionCode}/{companyCode}?api_token={api_token}")
                except requests.exceptions.ConnectionError:
                    return "Please check your internet connection"
                # Rate limited to the Starter API rate.
                time.sleep(80)
                data = r.json
                # print(data)

            if r.status_code == 401:
                return 'Invalid API Key'

            elif r.status_code == 403:
                return 'API Limit Reached'

            try:
                openCorporatesResults = data['results']['company']['officers'][:maxResults]
            except KeyError:
                continue

            for result in openCorporatesResults:
                if (result['officer']['inactive'] and considerInactive) or not result['officer']['inactive']:
                    index_of_child = len(returnResults)

                    returnResults.append([{'Full Name': result['officer']['name'],
                                           'Entity Type': 'Person'},
                                          {uid: {'Resolution': 'Officer',
                                                 'Notes': result['officer']['position']}}])

                    if result['officer']['end_date'] is not None:
                        returnResults.append(
                            [{'Date': result['officer']['end_date'], 'Entity Type': 'Date'},
                             {index_of_child: {'Resolution': 'Start Date', 'Notes': ''}}])

                    if result['officer']['start_date'] is not None:
                        returnResults.append(
                            [{'Date': result['officer']['start_date'], 'Entity Type': 'Date'},
                             {index_of_child: {'Resolution': 'Start Date', 'Notes': ''}}])

        return returnResults
