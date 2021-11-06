#!/usr/bin/env python3


class GetCollectionsInfo:
    name = "Get Collections Info"
    description = "Find information about Collections and their IDs"
    originTypes = {'Phrase'}
    resultTypes = {'Phrase, Aleph ID'}
    parameters = {'Max Results': {'description': 'Please enter the maximum number of results to return. ',
                                  'type': 'String',
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
        import time
        import requests
        from requests_futures.sessions import FuturesSession
        from concurrent.futures import as_completed

        returnResults = []
        futures = []
        uidList = []

        if parameters['Aleph Disclaimer'] != 'Accept':
            return "Please Accept the Terms for Aleph."

        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

        try:
            linkNumbers = int(parameters['Max Results'])
        except ValueError:
            return "The value for parameter 'Max Results' is not a valid integer."
        with FuturesSession(max_workers=15) as session:
            for entity in entityJsonList:
                uidList.append(entity['uid'])
                url = f"https://aleph.occrp.org/api/2/collections?offset=0&limit=300&page"
                time.sleep(1)
                futures.append(session.get(url, headers=headers))
        for future in as_completed(futures):
            uid = uidList[futures.index(future)]
            try:
                response = future.result().json()
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"

            max_results = int(len(response['results']))
            if linkNumbers == 0 or linkNumbers >= max_results:
                collections = response['results']
            else:
                collections = response['results'][0: linkNumbers]

            for collection in collections:
                index_of_child = len(returnResults)
                returnResults.append([{'Phrase': collection['label'],
                                       'Notes': str(collection.get('summary')),
                                       'Entity Type': 'Phrase'},
                                      {uid: {'Resolution': 'Aleph Collection Name',
                                             'Notes': ''}}])

                returnResults.append([{'ID': collection['id'],
                                       'Entity Type': 'Aleph ID'},
                                      {index_of_child: {'Resolution': 'Aleph Collection ID',
                                                        'Notes': ''}}])
        return returnResults
