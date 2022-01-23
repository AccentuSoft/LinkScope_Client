#!/usr/bin/env python3

class FramesLookUp:
    # A string that is treated as the name of this resolution.
    name = "Frames Look Up"

    # A string that describes this resolution.
    description = "Returns Frame Forms"

    originTypes = {'Form Field'}

    resultTypes = {'Edgar Company, Edgar ID, Country, Currency, Shares'}

    parameters = {
        'Quarter': {'description': 'Please Ensure that the selected Taxonomy matches the Form Field you typed',
                    'type': 'SingleChoice',
                    'value': {'January, February, and March (Q1)', 'April, May, and June (Q2)', 'July, August, and '
                                                                                                'September (Q3)',
                              'October, November, and December (Q4)'}},
        'Year': {'description': 'Please enter the year to match.',
                 'type': 'String',
                 'default': '2021'},
        'Max Results': {'description': 'Please enter the maximum number of results to return.\n'
                                       'Returns the 5 most recent by default.',
                        'type': 'String',
                        'default': '5'}}

    def resolution(self, entityJsonList, parameters):
        import requests
        import time

        headers = {
            'User-Agent': 'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        }

        try:
            linkNumbers = int(parameters['Max Results'])
        except ValueError:
            return "Invalid integer provided in 'Max Results' parameter"
        if linkNumbers <= 0:
            return []

        year = parameters['Year']
        quarterChoice = parameters['Quarter']
        quarter = quarterChoice[quarterChoice.find("(") + 1:quarterChoice.find(")")]
        returnResults = []

        for entity in entityJsonList:
            uid = entity['uid']
            unit = entity['Unit']
            taxonomy = entity['Taxonomy']
            form_field = entity['Field Name'].split(' ')[1]
            search_url = f'https://data.sec.gov/api/xbrl/frames/{taxonomy}/{form_field}/{unit}/CY{year}{quarter}I.json'
            time.sleep(1)
            r = requests.get(search_url, headers=headers)
            if r.status_code != 200:
                return []
            data = r.json()
            # print(data['data'])
            if linkNumbers > len(data['data']):
                linkNumbers = len(data['data'])

            for i in range(linkNumbers):
                # print(data['data'][i])
                index_of_child = (len(returnResults))
                returnResults.append([{'Company Name': data['data'][i]['entityName'],
                                       'Entity Type': 'Company'},
                                      {uid: {'Resolution': 'Edgar Company',
                                             'Name': 'Edgar Company',
                                             'Notes': ''}}])

                returnResults.append([{'CIK': str(data['data'][i]['cik']).zfill(10),
                                       'Entity Type': 'Edgar ID'},
                                      {index_of_child: {'Resolution': '',
                                                        'Name': '',
                                                        'Notes': ''}}])

                returnResults.append([{'Country Name': data['data'][i]['loc'],
                                       'Entity Type': 'Country'},
                                      {index_of_child: {'Resolution': '',
                                                        'Name': '',
                                                        'Notes': ''}}])
                if unit == 'USD':
                    returnResults.append([{'Amount': str(data['data'][i]['val']),
                                           'Currency Type': 'USD',
                                           'Entity Type': 'Currency'},
                                          {index_of_child: {'Resolution': 'Form Filed Value',
                                                            'Name': 'Edgar ID',
                                                            'Notes': ''}}])
                elif unit == 'shares':
                    returnResults.append([{'Amount': str(data['data'][i]['val']),
                                           'Entity Type': 'Shares'},
                                          {index_of_child: {'Resolution': 'Form Filed Value',
                                                            'Name': 'Edgar ID',
                                                            'Notes': ''}}])
        return returnResults
