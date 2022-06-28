#!/usr/bin/env python3


class BinaryEdgeHost:
    name = "BinaryEdge Host Query"
    category = "Network Infrastructure"
    description = "Get information about a host from BinaryEdge."
    originTypes = {"IP Address", "IPv6 Address"}
    resultTypes = {'Port'}
    parameters = {'BinaryEdge API Key': {'description': "Enter your BinaryEdge API key. Sign up for one at "
                                                        "https://www.binaryedge.io/",
                                         'type': 'String',
                                         'value': '',
                                         'global': True}}

    def resolution(self, entityJsonList, parameters):
        import requests
        import json

        baseURL = 'https://api.binaryedge.io/v2/query/ip/'
        requestHeaders = {'X-Key': parameters['BinaryEdge API Key'].strip()}

        returnResults = []

        for entity in entityJsonList:
            uid = entity['uid']
            if entity['Entity Type'] == 'IP Address':
                primaryField = entity['IP Address']
            elif entity['Entity Type'] == 'IPv6 Address':
                primaryField = entity['IPv6 Address']
            else:
                continue
            infoRequest = requests.get(baseURL + primaryField, headers=requestHeaders)
            statusCode = infoRequest.status_code

            if statusCode == 401:
                return "The BinaryEdge API key provided is not valid."
            elif statusCode == 403:
                return "The BinaryEdge API key provided does not have permission to access this resource."
            elif statusCode != 200:
                continue
            requestContent = json.loads(infoRequest.content)

            for event in requestContent['events']:
                for result in event['results']:
                    originDetails = result['origin']
                    targetDetails = result['target']
                    resultDetails = result['result']
                    if 'state' not in resultDetails['data']:
                        # Discard return result if it doesn't actually give us useful info about the state of the port.
                        # This happens in cases where the API returns stuff like the ciphers used in an SSH service.
                        #   There seems to always be a result with the simple port info, so we will use that one.
                        continue

                    returnResults.append([{'Port': targetDetails['ip'] + ':' + str(targetDetails['port']) + ':' +
                                                   targetDetails['protocol'],
                                           'State': resultDetails['data']['state']['state'],
                                           'Banner': resultDetails['data']['service'].get('banner', 'N/A'),
                                           'Product': resultDetails['data']['service'].get('product', 'Unknown'),
                                           'Entity Type': 'Port'},
                                          {uid: {'Resolution': 'BinaryEdge Scan Timestamp: ' + str(originDetails['ts']),
                                                 'Notes': ''}}])

        return returnResults
