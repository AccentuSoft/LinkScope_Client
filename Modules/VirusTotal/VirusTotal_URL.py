#!/usr/bin/env python3


class VirusTotal_URL:
    name = "VirusTotal URL Scan"
    category = "Threats & Malware"
    description = "Find information about a URL using VirusTotal.com"
    originTypes = {"Website"}
    resultTypes = {'Phrase'}
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
        from vtapi3 import VirusTotalAPIUrls, VirusTotalAPIError

        return_result = []
        api_key = parameters['VirusTotal API Key'].strip()
        vt_api_urls = VirusTotalAPIUrls(api_key)
        url = "https://www.virustotal.com/api/v3/analyses/"
        headers = {
            'x-apikey': api_key
        }

        for entity in entityJsonList:
            uid = entity['uid']
            primary_field = entity['URL'].strip()
            try:
                if not primary_field.startswith('http://') and not primary_field.startswith('https://'):
                    primary_field = f'http://{primary_field}'

                vtResult = vt_api_urls.upload(primary_field)
                if vt_api_urls.get_last_http_error() == vt_api_urls.HTTP_OK:
                    results = json.loads(vtResult)

                    while True:
                        response_req = requests.get(f"{url}{results['data']['id']}", headers=headers)
                        if response_req.status_code != 200:
                            return "Failed getting info from VirusTotal."
                        response = response_req.json()
                        if response['data']['status'] == 'completed':
                            break
                        time.sleep(5)

                    analysis_stats = response['data']['attributes']['last_analysis_stats']
                    return_result.append([{'Phrase': f"VirusTotal Scan Results for {primary_field}",
                                           'VT Malicious Votes': analysis_stats['malicious'],
                                           'VT Suspicious Votes': analysis_stats['suspicious'],
                                           'VT Harmless Votes': analysis_stats['harmless'],
                                           'VT Undetected Votes': analysis_stats['undetected'],
                                           'VT Timeout Votes': analysis_stats['timeout'],
                                           'Entity Type': 'Phrase'
                                           },
                                          {uid: {'Resolution': 'VirusTotal URL Scan', 'Notes': ''}}])

            except VirusTotalAPIError as e:
                return f"VirusTotal Error: {e}"
            finally:
                time.sleep(0.25)

        return return_result
