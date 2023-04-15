#!/usr/bin/env python3


class VirusTotal_IP_Address:
    name = "VirusTotal IP Address Scan"
    category = "Threats & Malware"
    description = "Find information about a IP address using VirusTotal.com"
    originTypes = {"IP Address"}
    resultTypes = {"Country", "Company", "Autonomous System", "Phrase"}
    parameters = {'VirusTotal API Key': {'description': 'Enter your api key under your profile after '
                                                        'signing up on https://virustotal.com. '
                                                        'Free usage of the API is limited to 500 requests per day '
                                                        'with a rate of 4 per minute.',
                                         'type': 'String',
                                         'value': '',
                                         'global': True}}

    def resolution(self, entityJsonList, parameters):
        import json
        from ipaddress import ip_address
        from vtapi3 import VirusTotalAPIIPAddresses, VirusTotalAPIError

        return_result = []
        api_key = parameters['VirusTotal API Key'].strip()
        vt_api_ip_addresses = VirusTotalAPIIPAddresses(api_key)
        for entity in entityJsonList:
            uid = entity['uid']
            primary_field = entity['IP Address'].strip()
            try:
                ip_address(primary_field)
            except ValueError:
                return "The Entity Provided isn't a valid IP Address"
            try:
                results = vt_api_ip_addresses.get_report(primary_field)
            except VirusTotalAPIError as err:
                return err, err.err_code
            else:
                if vt_api_ip_addresses.get_last_http_error() == vt_api_ip_addresses.HTTP_OK:
                    results = json.loads(results)
                    analysis_stats = results['data']['attributes']['last_analysis_stats']
                    return_result.append([{'Company Name': results['data']['attributes']['as_owner'],
                                           'Entity Type': 'Company'},
                                          {uid: {'Resolution': 'VirusTotal IP Scan', 'Notes': ''}}])
                    return_result.append([{'Country Name': results['data']['attributes']['country'],
                                           'Entity Type': 'Country'},
                                          {uid: {'Resolution': 'VirusTotal IP Scan', 'Notes': ''}}])
                    return_result.append([{'AS Number': "AS" + str(results['data']['attributes']['asn']),
                                           'Entity Type': 'Autonomous System'},
                                          {uid: {'Resolution': 'VirusTotal IP Scan', 'Notes': ''}}])
                    return_result.append([{'Phrase': f"VirusTotal Scan Results for {primary_field}",
                                           'VT Malicious Votes': analysis_stats['malicious'],
                                           'VT Suspicious Votes': analysis_stats['suspicious'],
                                           'VT Harmless Votes': analysis_stats['harmless'],
                                           'VT Undetected Votes': analysis_stats['undetected'],
                                           'VT Timeout Votes': analysis_stats['timeout'],
                                           'Entity Type': 'Phrase'
                                           },
                                          {uid: {'Resolution': 'VirusTotal IP Scan', 'Notes': ''}}])
                else:
                    continue
        return return_result
