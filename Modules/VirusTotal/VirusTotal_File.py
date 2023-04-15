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
        from time import sleep
        from pathlib import Path
        from datetime import datetime
        from vtapi3 import VirusTotalAPIFiles, VirusTotalAPIError

        return_result = []
        api_key = parameters['VirusTotal API Key'].strip()
        vt_files = VirusTotalAPIFiles(str(api_key))
        url = "https://www.virustotal.com/api/v3/analyses/"
        headers = {
            'x-apikey': api_key
        }
        for entity in entityJsonList:
            uid = entity['uid']
            file_path = Path(parameters['Project Files Directory']) / entity['File Path']
            if not file_path.exists() or not file_path.is_file():
                continue
            try:
                results = vt_files.upload(str(file_path))
            except VirusTotalAPIError as err:
                return f"VirusTotal Error: {str(err)}"
            else:
                if vt_files.get_last_http_error() != vt_files.HTTP_OK:
                    return f'HTTP Error: {vt_files.get_last_http_error()}'
                results = json.loads(results)
                while True:
                    response_req = requests.get(url + str(results['data']['id']), headers=headers)
                    response = response_req.json()
                    if response['data']['attributes']['status'] == 'completed':
                        break
                    sleep(5)
                harmless = response['data']['attributes']['stats']['harmless']
                suspicious = response['data']['attributes']['stats']['suspicious']
                malicious = response['data']['attributes']['stats']['malicious']
                undetected = response['data']['attributes']['stats']['undetected']
                unsupported = response['data']['attributes']['stats']['type-unsupported']
                return_result.append([{'Hash Value': response['meta']['file_info']['md5'],
                                       'Hash Algorithm': "MD5",
                                       'VT Malicious Votes': f"{malicious}",
                                       'VT Suspicious Votes': f"{suspicious}",
                                       'VT Harmless Votes': f"{harmless}",
                                       'VT Undetected Votes': f"{undetected}",
                                       'VT Unsupported Votes': f"{unsupported}",
                                       'Date Created': datetime.utcfromtimestamp(
                                           response['data']['attributes']['date']).strftime('%Y-%m-%dT%H:%M:%S'),
                                       'Entity Type': 'Hash'},
                                      {uid: {'Resolution': 'VirusTotal File Scan', 'Notes': ''}}])
        return return_result
