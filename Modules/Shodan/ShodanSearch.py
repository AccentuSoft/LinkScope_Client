#!/usr/bin/env python3


class ShodanSearch:
    name = "Shodan Database Search"
    category = "Network Infrastructure"
    description = "Search Shodan's database"
    originTypes = {'IP Address', 'Phrase', 'Person'}
    resultTypes = {'IP Address'}
    parameters = {'Shodan API Key': {'description': 'Enter your Premium API key under your profile after'
                                                    'signing up on https://shodan.io/ for more info on billing '
                                                    'plans:https://account.shodan.io/billing',
                                     'type': 'String',
                                     'value': '',
                                     'globals': True},

                  'Number of results': {'description': 'Creating a lot of nodes could slow down the software. Please '
                                                       'be mindful of the value you enter.',
                                        'type': 'String',
                                        'value': 'Enter the number of results you want returned',
                                        'default': '1'}
                  }

    def resolution(self, entityJsonList, parameters):
        import shodan

        return_result = []
        results_count = 0
        api_key = parameters['Shodan API Key'].strip()
        try:
            max_results = int(parameters['Number of results'])
        except ValueError:
            return "The value for parameter 'Max Results' is not a valid integer."
        api = shodan.Shodan(api_key)
        for entity in entityJsonList:
            uid = entity['uid']
            primary_field = entity[list(entity)[1]]
            try:
                search = api.search(primary_field)
            except shodan.exception.APIError:
                return "The API Key provided is Invalid"
            for match in search['matches'][:max_results]:
                return_result.append([{
                    'IP Address': str(match['ip_str']),
                    'Entity Type': 'IP Address'},
                    {uid: {'Resolution': 'Shodan Search results', 'Notes': ''}}])
        return return_result
