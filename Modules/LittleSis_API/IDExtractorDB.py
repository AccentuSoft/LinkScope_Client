class IDExtractorDB:
    # A string that is treated as the name of this resolution.
    name = "LittleSis ID Extractor"

    category = "LittleSis"

    # A string that describes this resolution.
    description = "Returns Nodes of ID Info"

    originTypes = {'Person', 'Phrase', 'Politically Exposed Person'}

    resultTypes = {'Politically Exposed Person', 'Little Sis ID'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import requests
        returnResults = []

        for entity in entityJsonList:
            uid = entity['uid']

            search_term = entity[list(entity)[1]]
            try:
                r = requests.get(
                    f'https://littlesis.org/api/entities/search?q={search_term}')
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"
            if r.status_code != 200:
                continue

            data = r.json()

            for data in data['data']:
                index_of_child = len(returnResults)
                returnResults.append([{'Full Name': data['attributes']['name'],
                                       'Date of Birth': str(data['attributes']['start_date']),
                                       'Occupation': ", ".join(data['attributes']['types']),
                                       'Notes': str(data['attributes']['blurb']),
                                       'Entity Type': 'Politically Exposed Person'},
                                      {uid: {'Resolution': 'Name in LittleSis DB',
                                             'Notes': ''}}])

                returnResults.append([{'ID': 'LS:' + str(data['attributes']['id']),
                                       'Entity Type': 'Little Sis ID'},
                                      {index_of_child: {'Resolution': 'ID in LittleSis DB',
                                                        'Notes': ''}}])
        return returnResults
