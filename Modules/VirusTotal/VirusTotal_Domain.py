#!/usr/bin/env python3


class VirusTotal_Domain:
    name = "VirusTotal Domain Scan"
    category = "Threats & Malware"
    description = "Find information about a domain using VirusTotal.com"
    originTypes = {"Domain"}
    resultTypes = {'Country', 'Domain', 'Company', 'Email Address', 'Phrase'}
    parameters = {'VirusTotal API Key': {'description': 'Enter your api key under your profile after '
                                                        'signing up on https://virustotal.com. '
                                                        'Free usage of the API is limited to 500 requests per day '
                                                        'with a rate of 4 per minute.',
                                         'type': 'String',
                                         'value': '',
                                         'global': True}}

    def resolution(self, entityJsonList, parameters):
        import json
        import hashlib
        from vtapi3 import VirusTotalAPIDomains, VirusTotalAPIError

        return_result = []
        api_key = parameters['VirusTotal API Key'].strip()
        vt_api_domains = VirusTotalAPIDomains(api_key)
        for entity in entityJsonList:
            uid = entity['uid']
            primary_field = entity['Domain Name'].strip()
            try:
                results = vt_api_domains.get_report(primary_field)
            except VirusTotalAPIError:
                continue
            else:
                if vt_api_domains.get_last_http_error() != vt_api_domains.HTTP_OK:
                    return f'HTTP Error [{vt_api_domains.get_last_http_error()}]'
                results = json.loads(results)
                analysis_stats = results['data']['attributes']['last_analysis_stats']

                return_result.append([{'Phrase': f"VirusTotal Scan Results for {primary_field}",
                                       'VT Malicious Votes': analysis_stats['malicious'],
                                       'VT Suspicious Votes': analysis_stats['suspicious'],
                                       'VT Harmless Votes': analysis_stats['harmless'],
                                       'VT Undetected Votes': analysis_stats['undetected'],
                                       'VT Timeout Votes': analysis_stats['timeout'],
                                       'Entity Type': 'Phrase'
                                       },
                                      {uid: {'Resolution': 'VirusTotal Domain Scan', 'Notes': ''}}])

                for result in results['data']['attributes']['last_dns_records']:
                    index_of_child = len(return_result)
                    dns_type = result['type']
                    value = result['value']
                    if dns_type == "A":
                        return_result.append([{'IP Address': value,
                                               'Entity Type': 'IP Address'},
                                              {index_of_child: {'Resolution': 'VirusTotal Domain A records',
                                                                'Notes': ''}}])
                    elif dns_type == "AAAA":
                        return_result.append([{'IPv6 Address': value,
                                               'Entity Type': 'IPv6 Address'},
                                              {uid: {'Resolution': 'VirusTotal Domain AAAA records', 'Notes': ''}}])
                    elif dns_type == "MX":
                        return_result.append([{'Domain Name': value,
                                               'Entity Type': 'Domain'},
                                              {uid: {'Resolution': 'VirusTotal Domain MX records', 'Notes': ''}}])
                    elif dns_type == "NS":
                        return_result.append([{'Domain Name': value,
                                               'Entity Type': 'Domain'},
                                              {uid: {'Resolution': 'VirusTotal NS records', 'Notes': ''}}])
                    elif dns_type == "SOA":
                        return_result.extend(
                            (
                                [{'Domain Name': result['rname'],
                                  'Entity Type': 'Domain'},
                                 {uid: {'Resolution': 'VirusTotal Domain SOA records',
                                        'Notes': ''}}],
                                [{'Domain Name': value,
                                  'Entity Type': 'Domain'},
                                 {index_of_child: {'Resolution': 'Start Of Authority DNS',
                                                   'Notes': ''}}]
                            )
                        )
                    elif dns_type == "TXT":
                        # Text records could be massive - do not want them breaking the UI
                        textPrimaryField = hashlib.md5(value.encode()).hexdigest()  # nosec
                        return_result.append(
                            [{'Phrase': f'{primary_field} TXT Record: {textPrimaryField}',
                              'Entity Type': 'Phrase',
                              'Notes': value},
                             {uid: {'Resolution': 'VirusTotal Domain TXT records',
                                    'Notes': ''}}]
                        )
                fields = results['data']['attributes']['whois'].split("\n")
                for field in fields:
                    field = field.split(":")
                    if field[0] == "Tech Organization":
                        return_result.append([{'Company Name': field[1],
                                               'Entity Type': 'Company'},
                                              {uid: {'Resolution': 'VirusTotal Domain Company', 'Notes': ''}}])
                    elif field[0] == "Tech Country":
                        return_result.append([{'Country Name': field[1],
                                               'Entity Type': 'Country'},
                                              {uid: {'Resolution': 'VirusTotal Domain Company Country',
                                                     'Notes': ''}}])
                    elif field[0] == "Registrar":
                        return_result.append([{'Company Name': field[1],
                                               'Entity Type': 'Company'},
                                              {uid: {'Resolution': 'VirusTotal Domain Registrar', 'Notes': ''}}])
                    elif field[0] == "Registrar Country":
                        return_result.append([{'Country Name': field[1],
                                               'Entity Type': 'Country'},
                                              {uid: {'Resolution': 'VirusTotal Domain Registrar Country',
                                                     'Notes': ''}}])
                    elif field[0] == "Registry Domain ID":
                        return_result.append(
                            [{'Phrase': f"{field[0]}:{field[1]}",
                              'Entity Type': 'Phrase'},
                             {uid: {'Resolution': 'VirusTotal Domain Registry ID',
                                    'Notes': ''}}]
                        )
                    elif field[0] == "Registrar IANA ID":
                        return_result.append(
                            [{'Phrase': f"{field[0]}:{field[1]}",
                              'Entity Type': 'Phrase'},
                             {uid: {'Resolution': 'VirusTotal Domain Registrar IANA ID',
                                    'Notes': ''}}]
                        )
                    elif field[0] == "Registrar Abuse Contact Email":
                        return_result.append([{'Email Address': field[1],
                                               'Entity Type': 'Email Address'},
                                              {uid: {'Resolution': 'VirusTotal Domain Email Address',
                                                     'Notes': ''}}])
        return return_result
