class ExtractRelationship:
    # A string that is treated as the name of this resolution.
    name = "LittleSis Relationship Extractor"

    # A string that describes this resolution.
    description = "Returns Nodes of Relationship Info"

    originTypes = {'Little Sis ID'}

    resultTypes = {'Currency', 'Politically Exposed Person', 'Little Sis ID'}

    parameters = {'Max Results': {'description': 'Please enter the maximum number of results to return. '
                                                 'Enter "0" (no quotes) to return all available results.',
                                  'type': 'String',
                                  'value': '',
                                  'default': '0'}}

    def resolution(self, entityJsonList, parameters):
        import time
        import requests
        import json
        returnResults = []
        index_of_child = []

        try:
            linkNumbers = int(parameters['Max Results'])
        except ValueError:
            return "Non-integer specified for 'Max Results' parameter; cannot run resolution."

        for entity in entityJsonList:
            uid = entity['uid']

            if not str(entity[list(entity)[1]]).startswith('LS:'):
                search_term = 'LS:' + entity[list(entity)[1]]
            else:
                search_term = entity[list(entity)[1]]

            term = (search_term.split(':')[1]).strip()
            try:
                apiRequest = requests.get(f'https://littlesis.org/api/entities/{term}/relationships')
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"
            if apiRequest.status_code != 200:
                continue

            data = apiRequest.json()

            data = data['data']
            if linkNumbers != 0:
                data = data[:linkNumbers]

            for relationship in data:
                index_of_child.append(len(returnResults))
                search_id = relationship['attributes']['entity1_id']

                if relationship['attributes']['description2'] is not None:
                    returnResults.append([{'ID': 'LS: ' + str(search_id),
                                           'Entity Type': 'Little Sis ID'},
                                          {uid: {'Resolution': str(relationship['attributes']['description2']),
                                                 'Is Current': str(relationship['attributes']['is_current']),
                                                 'Notes': str(relationship['attributes']['description2'])}}])
                elif relationship['attributes']['description1'] is not None:
                    returnResults.append([{'ID': 'LS: ' + str(search_id),
                                           'Entity Type': 'Little Sis ID'},
                                          {uid: {'Resolution': str(relationship['attributes']['description1']),
                                                 'Is Current': str(relationship['attributes']['is_current']),
                                                 'Notes': str(relationship['attributes']['description1'])}}])
                else:
                    returnResults.append([{'ID': 'LS: ' + str(search_id),
                                           'Entity Type': 'Little Sis ID'},
                                          {uid: {'Resolution': str(relationship['attributes']['description']),
                                                 'Is Current': str(relationship['attributes']['is_current']),
                                                 'Notes': str(relationship['attributes']['description'])}}])

                try:
                    res = requests.get(f'https://littlesis.org/api/entities/{search_id}')
                    time.sleep(0.2)
                except requests.exceptions.ConnectionError:
                    return "Please check your internet connection"
                if apiRequest.status_code != 200:
                    return returnResults

                try:
                    entity_data = res.json()
                except json.decoder.JSONDecodeError:
                    continue
                child_of_child = len(returnResults)

                returnResults.append([{'Full Name': entity_data['data']['attributes']['name'],
                                       'Occupation': ", ".join(entity_data['data']['attributes']['types']),
                                       'Notes': entity_data['data']['attributes']['blurb'],
                                       'Entity Type': 'Politically Exposed Person'},
                                      {index_of_child[-1]: {'Resolution': 'Name in LittleSis DB',
                                                            'Notes': ''}}])

                if relationship['attributes']['amount'] is not None:
                    returnResults.append([{'Amount': str(relationship['attributes']['amount']),
                                           'Currency Type': relationship['attributes']['currency'],
                                           'Entity Type': 'Currency'},
                                          {child_of_child: {'Resolution': 'Contribution Amount',
                                                            'Notes': ''}}])

        return returnResults
