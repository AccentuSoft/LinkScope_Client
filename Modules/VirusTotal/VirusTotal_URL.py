#!/usr/bin/env python3


class VirusTotal_URL:
    name = "VirusTotal URL Scan"
    category = "Threats & Malware"
    description = "Find information about a URL using VirusTotal.com"
    originTypes = {"Website"}
    resultTypes = {'Phrase'}
    parameters = {'VirusTotal API Key': {'description': 'Enter your api key under your profile after'
                                                        ' signing up on https://virustotal.com. '
                                                        'Free usage of the API is limited to 1,000 requests '
                                                        'with a rate of 4 per minute.',
                                         'type': 'String',
                                         'value': '',
                                         'global': True}}

    def resolution(self, entityJsonList, parameters):
        import json
        import requests
        import time
        from vtapi3 import VirusTotalAPIUrls, VirusTotalAPIError

        return_result = []
        api_key = parameters['VirusTotal API Key']
        vt_api_urls = VirusTotalAPIUrls(api_key)
        url = "https://www.virustotal.com/api/v3/analyses/"

        def getVirusTotalResults(entityPrimaryField):
            vtResult = vt_api_urls.upload(entityPrimaryField)
            if vt_api_urls.get_last_http_error() == vt_api_urls.HTTP_OK:
                results = json.loads(vtResult)
                results = json.dumps(results, sort_keys=False)
                headers = {
                    'x-apikey': api_key
                }
                results = json.loads(results)
                response = requests.get(url + str(results['data']['id']), headers=headers)
                response = response.json()
                queryID = response['meta']['url_info']['id']
                harmless = response['data']['attributes']['stats']['harmless']
                suspicious = response['data']['attributes']['stats']['suspicious']
                malicious = response['data']['attributes']['stats']['malicious']
                undetected = response['data']['attributes']['stats']['undetected']
                return queryID, harmless, suspicious, malicious, undetected
            else:
                return "An error occurred"

        for entity in entityJsonList:
            uid = entity['uid']
            primary_field = entity[list(entity)[1]].strip()
            try:
                if not primary_field.startswith('http://') and not primary_field.startswith('https://'):
                    primary_field = 'http://' + primary_field
                result = getVirusTotalResults(primary_field)
                while result is None or int(result[1]) + int(result[2]) + int(result[3]) + int(result[4]) == 0:
                    time.sleep(5)
                    result = getVirusTotalResults(primary_field)

                return_result.append([{'Phrase': result[0],
                                       'Notes': "Harmless:" + " " + str(result[1]) + " \n" +
                                                "Malicious:" + " " + str(result[3]) + "\n" +
                                                "Suspicious:" + " " + str(result[2]) + "\n" +
                                                "Undetected:" + " " + str(result[4]),
                                       'Entity Type': 'Phrase'},
                                      {uid: {'Resolution': 'VirusTotal URL Scan', 'Notes': ''}}])

            except VirusTotalAPIError:
                continue
            finally:
                time.sleep(0.25)

        return return_result
