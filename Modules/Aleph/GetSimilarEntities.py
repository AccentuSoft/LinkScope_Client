#!/usr/bin/env python3


class GetSimilarEntities:
    name = "Get Similar Entities"
    description = "Find information about similar entities"
    originTypes = {'Phrase', 'Person', 'Politically Exposed Person'}
    resultTypes = {'Phrase', 'Person', 'Address', 'Aleph ID'}
    parameters = {'Aleph Disclaimer': {'description': 'The content on Aleph is provided for general information only.\n'
                                                      'It is not intended to amount to advice on which you should place'
                                                      'sole and entire reliance.\n'
                                                      'We recommend that you conduct your own independent fact checking'
                                                      'against the data and materials that you access on Aleph.\n'
                                                      'Aleph API is not a replacement for traditional due diligence '
                                                      'checks and know-your-customer background checks.',
                                       'type': 'String',
                                       'value': 'Type "Accept" (without quotes) to confirm your understanding.',
                                       'global': True}}

    def resolution(self, entityJsonList, parameters):
        import time
        import requests
        import pycountry
        from requests_futures.sessions import FuturesSession
        from concurrent.futures import as_completed

        returnResults = []
        futures = []
        uidList = []

        if parameters['Aleph Disclaimer'] != 'Accept':
            return "Please Accept the Terms for Aleph."

        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        with FuturesSession(max_workers=15) as session:
            for entity in entityJsonList:
                uidList.append(entity['uid'])
                primary_field = entity[list(entity)[1]].strip()
                url = f"https://aleph.occrp.org/api/2/entities/{primary_field}/similar"
                time.sleep(1)
                futures.append(session.get(url, headers=headers))
        for future in as_completed(futures):
            uid = uidList[futures.index(future)]
            try:
                response = future.result().json()
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"
            entities = response['results']
            for schema in entities:
                if schema['entity']['schema'] == 'Person':
                    index_of_child = len(returnResults)
                    returnResults.append([{'Full Name': ' '.join(map(str, schema['entity']['properties']['name'])),
                                           'Gender': ' '.join(map(str, schema['entity']['properties']['gender'])),
                                           'Notes': ' '.join(map(str, schema['entity']['properties']['legalForm'])),
                                           'Entity Type': 'Person'},
                                          {uid: {'Resolution': 'Person Entity',
                                                 'Notes': ''}}])
                    country = pycountry.countries.get(alpha_2=schema['entity']['properties']['country'][0]).name
                    returnResults.append([{'Street Address': schema['entity']['properties']['addressEntity'][0]
                                           ['properties']['full'][0],
                                           'Postal Code': schema['entity']['properties']['addressEntity'][0]
                                           ['properties']['postalCode'][0],
                                           'Country': country,
                                           'Entity Type': 'Address'},
                                          {index_of_child: {'Resolution': 'Address',
                                                            'Notes': ''}}])
                    returnResults.append([{'Phrase': schema['entity']['collection']['label'],
                                           'Notes': schema['entity']['collection']['summary'],
                                           'Entity Type': 'Phrase'},
                                          {index_of_child: {'Resolution': 'Location in Database',
                                                            'Notes': ''}}])

                    returnResults.append([{'ID': schema['entity']['id'],
                                           'Entity Type': 'Aleph ID'},
                                          {index_of_child: {'Resolution': 'ID in Database',
                                                            'Notes': ''}}])

                elif schema['entity']['schema'] == 'Company':
                    index_of_child = len(returnResults)
                    returnResults.append([{'Company Name': ' '.join(map(str, schema['entity']['properties']['name'])),
                                           'Notes': str(schema['entity']['properties']['status']),
                                           'Entity Type': 'Company'},
                                          {uid: {'Resolution': 'Company Entity',
                                                 'Notes': ''}}])
                    country = pycountry.countries.get(alpha_2=schema['entity']['properties']['country'][0]).name
                    returnResults.append([{'Street Address': str(schema['entity']['properties'].get('address')),
                                           'Country': country,
                                           'Entity Type': 'Address'},
                                          {index_of_child: {'Resolution': 'Address',
                                                            'Notes': ''}}])
                    returnResults.append([{'Phrase': schema['entity']['collection']['label'],
                                           'Notes': schema['entity']['collection']['summary'],
                                           'Entity Type': 'Phrase'},
                                          {index_of_child: {'Resolution': 'Location in Database',
                                                            'Notes': ''}}])

                    returnResults.append([{'ID': schema['entity']['id'],
                                           'Entity Type': 'Aleph ID'},
                                          {index_of_child: {'Resolution': 'ID in Database',
                                                            'Notes': ''}}])
        return returnResults
