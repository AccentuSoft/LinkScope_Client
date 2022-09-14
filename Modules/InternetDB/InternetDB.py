#!/usr/bin/env python3


class InternetDB:
    name = "InternetDB IP lookup"
    category = "Network Infrastructure"
    description = "Convert the primary field of selected entities to a Phrase entity."
    originTypes = {'IP Address'}
    resultTypes = {'Domain', 'Phrase', 'Port'}

    parameters = {'InternetDB Disclaimer': {'description': 'InternetDB access is free for non-commercial use. '
                                                           'If you are using this service for commercial purposes, '
                                                           'you need an enterprise license. You can get one at '
                                                           'https://enterprise.shodan.io/.\n'
                                                           'Type "Accept" (without quotes) to confirm your '
                                                           'understanding.',
                                            'type': 'String',
                                            'value': 'Type "Accept" (without quotes) to confirm your understanding.',
                                            'global': True}}

    def resolution(self, entityJsonList, parameters):
        import requests

        if parameters['InternetDB Disclaimer'].strip() != 'Accept':
            return []

        returnResults = []

        for entity in entityJsonList:
            primaryField = entity['IP Address']
            entityUID = entity['uid']
            requestResult = requests.get("https://internetdb.shodan.io/" + primaryField).json()

            if "detail" in requestResult:
                returnResults.append([{'Phrase': requestResult['detail'],
                                       'Entity Type': 'Phrase'},
                                      {entityUID: {'Resolution': 'InternetDB Lookup Result',
                                                   'Notes': ''}}])
            elif "msg" in requestResult:
                returnResults.append([{'Phrase': requestResult['msg'],
                                       'Entity Type': 'Phrase'},
                                      {entityUID: {'Resolution': 'InternetDB Lookup Result',
                                                   'Notes': ''}}])
            else:
                for cpe in requestResult['cpes']:
                    returnResults.append([{'Phrase': cpe,
                                           'Entity Type': 'Phrase'},
                                          {entityUID: {'Resolution': 'InternetDB IP CPE',
                                                       'Notes': ''}}])
                for hostname in requestResult['hostnames']:
                    returnResults.append([{'Domain Name': hostname,
                                           'Entity Type': 'Domain'},
                                          {entityUID: {'Resolution': 'InternetDB IP Domain',
                                                       'Notes': ''}}])
                for port in requestResult['ports']:
                    returnResults.append([{'Port': requestResult['ip'] + ":" + str(port),
                                           'Entity Type': 'Port'},
                                          {entityUID: {'Resolution': 'InternetDB IP Open Port',
                                                       'Notes': ''}}])
                for tag in requestResult['tags']:
                    returnResults.append([{'Phrase': tag,
                                           'Entity Type': 'Phrase'},
                                          {entityUID: {'Resolution': 'InternetDB IP Tag',
                                                       'Notes': ''}}])
                for vuln in requestResult['vulns']:
                    returnResults.append([{'Phrase': vuln,
                                           'Entity Type': 'Phrase'},
                                          {entityUID: {'Resolution': 'InternetDB IP Vuln',
                                                       'Notes': ''}}])

        return returnResults
