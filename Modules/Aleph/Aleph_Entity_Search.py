#!/usr/bin/env python3


class Aleph_Entity_Search:
    name = "Aleph Entity Search"
    category = "Aleph OCCRP"
    description = "Find information about a given search parameter"
    originTypes = {'Phrase', 'Person', 'Politically Exposed Person'}
    resultTypes = {'Phrase'}
    parameters = {'Number of results': {'description': 'Creating a lot of nodes could slow down the software. Please '
                                                       'be mindful of the value you enter.',
                                        'type': 'String',
                                        'value': 'Enter the number of results you want returned',
                                        'default': '1'},
                  'Aleph Disclaimer': {'description': 'The content on Aleph is provided for general information only.\n'
                                                      'It is not intended to amount to advice on which you should place'
                                                      'sole and entire reliance.\n'
                                                      'We recommend that you conduct your own independent fact checking'
                                                      'against the data and materials that you access on Aleph.\n'
                                                      'Aleph API is not a replacement for traditional due diligence '
                                                      'checks and know-your-customer background checks.',
                                       'type': 'String',
                                       'value': 'Type "Accept" (without quotes) to confirm your understanding.',
                                       'global': True}
                  }

    def resolution(self, entityJsonList, parameters):
        import requests
        import pycountry
        import time
        from requests_futures.sessions import FuturesSession
        from concurrent.futures import as_completed

        return_result = []
        uidList = []
        futures = []

        url = "https://aleph.occrp.org/api/2/entities"
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        gender = "None"

        if parameters['Aleph Disclaimer'] != 'Accept':
            return "Please Accept the Terms for Aleph."

        try:
            max_results = int(parameters['Number of results'])
        except ValueError:
            return "The value for parameter 'Max Results' is not a valid integer."
        with FuturesSession(max_workers=15) as session:
            for entity in entityJsonList:
                uidList.append(entity['uid'])
                primary_field = entity[list(entity)[1]].strip()
                crafted_url = url + f"?q={primary_field}&filter:schemata=Thing&limit={max_results}"
                time.sleep(1)
                futures.append(session.get(crafted_url, headers=headers))
        for future in as_completed(futures):
            uid = uidList[futures.index(future)]
            try:
                response = future.result().json()
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"
            # print(response)
            for schema in response['results']:
                index_of_child = len(return_result)
                try:
                    if schema['schema'] == "Person":
                        if schema['properties'].get('gender') is not None \
                                and schema['properties'].get('gender')[0] == "F":
                            gender = "Female"
                        elif schema['properties'].get('gender') is not None \
                                and schema['properties'].get('gender')[0] == "M":
                            gender = "Male"
                        if schema['properties'].get('legalForm') is not None:
                            return_result.append(
                                [{'Full Name': schema['properties']['name'][0],
                                  'Gender': gender,
                                  'Date Of Birth': str(schema['properties'].get('birthDate')),
                                  'Notes': f"{schema['links']['self']}\nLegal Form: {schema['properties']['legalForm'][0]}",
                                  'Entity Type': 'Person'},
                                 {uid: {'Resolution': 'Person Entity', 'Notes': ''}}])
                        else:
                            return_result.append(
                                [{'Full Name': str(schema['properties']['name'][0]),
                                  'Gender': gender,
                                  'Date Of Birth': str(schema['properties']['birthDate'][0]),
                                  'Notes': schema['links']['self'],
                                  'Entity Type': 'Person'},
                                 {uid: {'Resolution': 'Person Entity', 'Notes': ''}}])
                        if schema['properties'].get('registrationNumber') is not None:
                            return_result.append(
                                [{'Registration Number': str(schema['properties']['registrationNumber'][0]),
                                  'Notes': '',
                                  'Entity Type': 'Company'},
                                 {index_of_child: {'Resolution': 'Aleph Registration Number', 'Notes': ''}}])
                        if schema['properties'].get('country') is not None:
                            return_result.append(
                                [{'Country Name': str(
                                    pycountry.countries.get(alpha_2=schema['properties']['country'][0]).name),
                                    'Notes': '',
                                    'Entity Type': 'Country'},
                                    {index_of_child: {'Resolution': 'Country of Origin', 'Notes': ''}}])
                        if schema['properties'].get('addressEntity'):
                            return_result.append(
                                [{'Street Address': str(
                                    schema['properties']['addressEntity'][0]['properties']['full'][0]),
                                    'Notes': '',
                                    'Entity Type': 'Address'},
                                    {index_of_child: {'Resolution': 'Address Entity', 'Notes': ''}}])
                        else:
                            return_result.append(
                                [{'Street Address': str(schema['properties']['address'][0]),
                                  'Notes': '',
                                  'Entity Type': 'Address'},
                                 {index_of_child: {'Resolution': 'Address Entity', 'Notes': ''}}])
                        return_result.append(
                            [{'ID': str(schema['id']),
                              'Notes': '',
                              'Entity Type': 'Aleph ID'},
                             {index_of_child: {'Resolution': 'Aleph ID', 'Notes': ''}}])
                        return_result.append(
                            [{'Phrase': str(schema['collection']['label']),
                              'Notes': str(schema['collection']['summary']),
                              'Entity Type': 'Phrase'},
                             {index_of_child: {'Resolution': 'Aleph Collection', 'Notes': ''}}])
                        return_result.append(
                            [{'ID': str(schema['collection']['collection_id']),
                              'Notes': '',
                              'Entity Type': 'Aleph Collection ID'},
                             {index_of_child: {'Resolution': 'Aleph Collection ID', 'Notes': ''}}])
                    elif schema['schema'] == "Organization":
                        return_result.append(
                            [{'Organization Name': str(schema['properties']['name'][0]),
                              'Registration Number': str(schema['properties']['registrationNumber'][0]),
                              'Notes': f"{schema['links']['self']}\nLegal Form: {schema['properties']['legalForm'][0]}\n"
                                       f"Source URL: {schema['properties']['sourceUrl'][0]}",
                              'Entity Type': 'Organization'},
                             {uid: {'Resolution': 'Aleph Organisation Entity', 'Notes': ''}}])
                        return_result.append(
                            [{'Country Name': str(
                                pycountry.countries.get(alpha_2=schema['properties']['country'][0]).name),
                                'Notes': '',
                                'Entity Type': 'Country'},
                                {index_of_child: {'Resolution': "Aleph Organisation Country", 'Notes': ''}}])
                        return_result.append(
                            [{'Street Address': str(schema['properties']['address'][0]),
                              'Notes': '',
                              'Entity Type': 'Address'},
                             {index_of_child: {'Resolution': "Aleph Organisation Address", 'Notes': ''}}])
                        return_result.append(
                            [{'ID': str(schema['id']),
                              'Notes': '',
                              'Entity Type': 'Aleph ID'},
                             {index_of_child: {'Resolution': "Aleph Organisation ID", 'Notes': ''}}])
                        return_result.append(
                            [{'Phrase': str(schema['collection']['label']),
                              'Notes': str(schema['collection']['summary']),
                              'Entity Type': 'Phrase'},
                             {index_of_child: {'Resolution': 'Aleph Collection', 'Notes': ''}}])
                        return_result.append(
                            [{'Phone Number': str(schema['properties']['phone'][0]),
                              'Notes': '',
                              'Entity Type': 'Phone Number'},
                             {index_of_child: {'Resolution': 'Phone Number', 'Notes': ''}}])
                        return_result.append(
                            [{'Phrase': str(schema['properties']['classification'][0]),
                              'Notes': '',
                              'Entity Type': 'Phrase'},
                             {index_of_child: {'Resolution': 'Organisation Classification', 'Notes': ''}}])
                        return_result.append(
                            [{'Phrase': str(schema['collection']['collection_id']),
                              'Notes': '',
                              'Entity Type': 'Phrase'},
                             {index_of_child: {'Resolution': 'Aleph Collection ID', 'Notes': ''}}])
                    elif schema['schema'] == "Pages":
                        if 'updated_at' in schema:
                            date_created = schema['updated_at']
                        else:
                            date_created = schema['created_at']
                        doc_name = 'Document: ' + schema['properties']['title'][0]
                        entity_link = schema['links']['self']
                        file_link = schema['links']['file']
                        source_url = schema['properties']['sourceUrl'][0]
                        return_result.append(
                            [{'Phrase': doc_name,
                              'Source': source_url,
                              'Notes': 'Link to Aleph Entity: ' + entity_link + '\n\n' +
                                       'Link to document: ' + file_link,
                              'Entity Type': 'Phrase',
                              'Date Created': date_created},
                             {uid: {'Resolution': 'Aleph Document', 'Notes': ''}}])
                    elif schema['properties']['parent'][0]['schema'] == "Person":
                        gender = str(schema['properties']['parent'][0]['properties'].get('gender')[0])
                        if schema['properties']['parent'][0]['properties'].get('legalForm') is not None:
                            return_result.append(
                                [{'Full Name': schema['properties']['parent'][0]['properties']['name'][0],
                                  'Gender': gender,
                                  'Date Of Birth': str(schema['properties']['parent'][0]['properties']['birthDate'][0]),
                                  'Notes': f"{schema['properties']['parent'][0]['links']['self']}\nLegal Form: "
                                           f"{schema['properties']['parent'][0]['properties']['legalForm'][0]}",
                                  'Entity Type': 'Person'},
                                 {uid: {'Resolution': 'Aleph Person Entity', 'Notes': ''}}])
                        else:
                            return_result.append(
                                [{'Full Name': schema['properties']['parent'][0]['properties']['name'][0],
                                  'Gender': gender,
                                  'Date Of Birth': str(schema['properties']['parent'][0]['properties']['birthDate'][0]),
                                  'Notes': schema['properties']['parent'][0]['links']['self'],
                                  'Entity Type': 'Person'},
                                 {uid: {'Resolution': 'Aleph Person Entity', 'Notes': ''}}])
                        if schema['properties']['parent'][0]['properties'].get('registrationNumber') is not None:
                            return_result.append(
                                [{'Registration Number': str(
                                    schema['properties']['parent'][0]['properties']['registrationNumber'][0]),
                                    'Notes': '',
                                    'Entity Type': 'Company'},
                                    {index_of_child: {'Resolution': 'Company Registration Number', 'Notes': ''}}])
                        if schema['properties']['parent'][0]['properties'].get('country') is not None:
                            return_result.append(
                                [{'Country Name': str(
                                    pycountry.countries.get(
                                        alpha_2=schema['properties']['parent'][0]['properties']['country'][0]).name),
                                    'Notes': '',
                                    'Entity Type': 'Country'},
                                    {index_of_child: {'Resolution': 'Country', 'Notes': ''}}])
                        return_result.append(
                            [{'ID': str(schema['properties']['parent'][0]['id']),
                              'Notes': '',
                              'Entity Type': 'Aleph ID'},
                             {index_of_child: {'Resolution': 'Aleph ID', 'Notes': ''}}])
                        return_result.append(
                            [{'Phrase': str(schema['properties']['parent'][0]['collection']['label']),
                              'Notes': str(schema['properties']['parent'][0]['collection']['summary']),
                              'Entity Type': 'Phrase'},
                             {index_of_child: {'Resolution': 'Aleph Collection Entity', 'Notes': ''}}])
                        return_result.append(
                            [{'Phrase': str(schema['properties']['parent'][0]['collection']['collection_id']),
                              'Notes': '',
                              'Entity Type': 'Phrase'},
                             {index_of_child: {'Resolution': 'Aleph Collection ID', 'Notes': ''}}])
                        index_of_child_of_child = len(return_result)
                        return_result.append(
                            [{'Company Name': str(schema['properties']['name'][0]),
                              'Notes': schema['links']['self'],
                              'Entity Type': 'Company'},
                             {index_of_child: {'Resolution': 'Aleph Company Entity', 'Notes': ''}}])
                        return_result.append(
                            [{'Street Address': str(schema['properties']['addressEntity'][0]['properties']['full'][0]),
                              'Notes': '',
                              'Entity Type': 'Address'},
                             {index_of_child_of_child: {'Resolution': 'Aleph Person Address', 'Notes': ''}}])
                        for country_code in schema['collection']['countries']:
                            return_result.append(
                                [{'Country Name': str(pycountry.countries.get(alpha_2=country_code).name),
                                  'Notes': '',
                                  'Entity Type': 'Country'},
                                 {index_of_child_of_child: {'Resolution': 'Country', 'Notes': ''}}])
                        return_result.append(
                            [{'Phrase': str(schema['collection']['label']),
                              'Notes': str(schema['collection']['summary']),
                              'Entity Type': 'Phrase'},
                             {index_of_child_of_child: {'Resolution': 'Aleph Collection Entity', 'Notes': ''}}])
                        return_result.append(
                            [{'ID': str(schema['collection']['collection_id']),
                              'Notes': '',
                              'Entity Type': 'Aleph Collection ID'},
                             {index_of_child_of_child: {'Resolution': 'Aleph Entity Search', 'Notes': ''}}])
                except (TypeError, KeyError):
                    # print(repr(e))
                    continue
        return return_result
