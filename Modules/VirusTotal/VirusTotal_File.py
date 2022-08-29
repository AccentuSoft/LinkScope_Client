#!/usr/bin/env python3


class VirusTotal_File:
    name = "VirusTotal File Scan"
    category = "Threats & Malware"
    description = "Find information about a file using VirusTotal.com"
    originTypes = {"Image", "Document", "Archive"}
    resultTypes = {'Hash'}
    parameters = {'VirusTotal API Key': {'description': 'Enter your api key under your profile after'
                                                        ' signing up on https://virustotal.com. '
                                                        'Free usage of the API is limited to 500 requests per day '
                                                        'with a rate of 4 per minute.',
                                         'type': 'String',
                                         'value': '',
                                         'global': True}}

    def resolution(self, entityJsonList, parameters):
        import json
        import requests
        import time
        from pathlib import Path
        from datetime import datetime
        from vtapi3 import VirusTotalAPIFiles, VirusTotalAPIError

        return_result = []
        api_key = parameters['VirusTotal API Key'].strip()
        vt_files = VirusTotalAPIFiles(str(api_key))
        url = "https://www.virustotal.com/api/v3/analyses/"
        for entity in entityJsonList:
            uid = entity['uid']
            file_path = Path(parameters['Project Files Directory']) / entity['File Path']
            if not (file_path.exists() and file_path.is_file()):
                continue
            try:
                results = vt_files.upload(str(file_path))
            except VirusTotalAPIError as err:
                return "VirusTotal Error: " + str(err)
            else:
                if vt_files.get_last_http_error() == vt_files.HTTP_OK:
                    results = json.loads(results)
                    results = json.dumps(results, sort_keys=False, indent=4)
                    headers = {
                        'x-apikey': api_key
                    }
                    results = json.loads(results)
                    response = requests.get(url + str(results['data']['id']), headers=headers)
                    response = response.json()
                    harmless = response['data']['attributes']['stats']['harmless']
                    suspicious = response['data']['attributes']['stats']['suspicious']
                    malicious = response['data']['attributes']['stats']['malicious']
                    undetected = response['data']['attributes']['stats']['undetected']
                    while undetected == 0 and malicious == 0 and suspicious == 0 and harmless == 0:
                        time.sleep(7)
                        self.resolution(entityJsonList, parameters)
                    return_result.append([{'Hash Value': response['meta']['file_info']['md5'],
                                           'Hash Algorithm': "MD5",
                                           'Notes': "Harmless:" + " " + str(
                                               harmless) + "\n" +
                                                    "Malicious:" + " " + str(
                                               malicious) + "\n" +
                                                    "Suspicious:" + " " + str(
                                               suspicious) + "\n" +
                                                    "Undetected:" + " " + str(
                                               undetected) + "\n" +
                                                    "Type Unsupported" + " " + str(
                                               response['data']['attributes']['stats']['type-unsupported']),
                                           'Date Created': datetime.utcfromtimestamp(
                                               response['data']['attributes']['date']).strftime('%Y-%m-%dT%H:%M:%S'),
                                           'Entity Type': 'Hash'},
                                          {uid: {'Resolution': 'VirusTotal File Scan', 'Notes': ''}}])
                else:
                    return 'HTTP Error [' + str(vt_files.get_last_http_error()) + ']'
            return return_result
