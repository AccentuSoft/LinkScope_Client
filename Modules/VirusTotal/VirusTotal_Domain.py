#!/usr/bin/env python3


class VirusTotal_Domain:
    name = "VirusTotal Domain Scan"
    category = "Threats & Malware"
    description = "Find information about a domain using VirusTotal.com"
    originTypes = {"Domain"}
    resultTypes = {'Country', 'Domain', 'Company', 'Email Address', 'Phrase'}
    parameters = {'VirusTotal API Key': {'description': 'Enter your api key under your profile after'
                                                        ' signing up on https://virustotal.com. '
                                                        'Free usage of the API is limited to 500 requests per day '
                                                        'with a rate of 4 per minute.',
                                         'type': 'String',
                                         'value': '',
                                         'global': True}}

    def resolution(self, entityJsonList, parameters):
        import json
        import hashlib
        from binascii import hexlify
        from vtapi3 import VirusTotalAPIDomains, VirusTotalAPIError

        return_result = []
        api_key = parameters['VirusTotal API Key'].strip()
        vt_api_domains = VirusTotalAPIDomains(api_key)
        for entity in entityJsonList:
            uid = entity['uid']
            primary_field = entity[list(entity)[1]].strip()
            try:
                results = vt_api_domains.get_report(primary_field)
            except VirusTotalAPIError:
                continue
            else:
                if vt_api_domains.get_last_http_error() == vt_api_domains.HTTP_OK:
                    results = json.loads(results)
                    results = json.dumps(results, sort_keys=False, indent=4)
                    results = json.loads(results)
                    for result in results['data']['attributes']['last_dns_records']:
                        index_of_child = len(return_result)
                        dns_type = result['type']
                        value = result['value']
                        if dns_type == "MX":
                            return_result.append([{'Domain Name': value,
                                                   'Entity Type': 'Domain'},
                                                  {uid: {'Resolution': 'VirusTotal Domain MX records', 'Notes': ''}}])
                        elif dns_type == "A":
                            return_result.append([{'IP Address': value,
                                                   'Entity Type': 'IP Address'},
                                                  {index_of_child: {'Resolution': 'VirusTotal Domain A records',
                                                                    'Notes': ''}}])
                        elif dns_type == "AAAA":
                            return_result.append([{'IPv6 Address': value,
                                                   'Entity Type': 'IPv6 Address'},
                                                  {uid: {'Resolution': 'VirusTotal Domain AAAA records', 'Notes': ''}}])
                        elif dns_type == "TXT":
                            # Text records could be massive - do not want them breaking the UI
                            textPrimaryField = hashlib.md5(value.encode())  # nosec
                            return_result.append([{'Phrase': primary_field + ' TXT Record: ' +
                                                             hexlify(textPrimaryField.digest()).decode(),
                                                   'Entity Type': 'Phrase',
                                                   'Notes': value},
                                                  {uid: {'Resolution': 'VirusTotal Domain TXT records', 'Notes': ''}}])
                        elif dns_type == "SOA":
                            return_result.append([{'Domain Name': result['rname'],
                                                   'Entity Type': 'Domain'},
                                                  {uid: {'Resolution': 'VirusTotal Domain SOA records', 'Notes': ''}}])
                            return_result.append([{'Domain Name': value,
                                                   'Entity Type': 'Domain'},
                                                  {index_of_child: {'Resolution': 'Start Of Authority DNS',
                                                                    'Notes': ''}}])
                        elif dns_type == "NS":
                            return_result.append([{'Domain Name': value,
                                                   'Entity Type': 'Domain'},
                                                  {uid: {'Resolution': 'VirusTotal NS records', 'Notes': ''}}])
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
                                                         'notes': ''}}])
                        elif field[0] == "Registrar":
                            return_result.append([{'Company Name': field[1],
                                                   'Entity Type': 'Company'},
                                                  {uid: {'Resolution': 'VirusTotal Domain Registrar', 'notes': ''}}])
                        elif field[0] == "Registrar Country":
                            return_result.append([{'Country Name': field[1],
                                                   'Entity Type': 'Country'},
                                                  {uid: {'Resolution': 'VirusTotal Domain Registrar Country',
                                                         'notes': ''}}])
                        elif field[0] == "Registry Domain ID":
                            return_result.append([{'Phrase': field[0] + ":" + field[1],
                                                   'Entity Type': 'Phrase'},
                                                  {uid: {'Resolution': 'VirusTotal Domain Registry ID', 'notes': ''}}])
                        elif field[0] == "Registrar IANA ID":
                            return_result.append([{'Phrase': field[0] + ":" + field[1],
                                                   'Entity Type': 'Phrase'},
                                                  {uid: {'Resolution': 'VirusTotal Domain Registrar IANA ID',
                                                         'notes': ''}}])
                        elif field[0] == "Registrar Abuse Contact Email":
                            return_result.append([{'Email Address': field[1],
                                                   'Entity Type': 'Email Address'},
                                                  {uid: {'Resolution': 'VirusTotal Domain Email Address',
                                                         'notes': ''}}])
                else:
                    return f'HTTP Error [' + str(vt_api_domains.get_last_http_error()) + ']'
            return return_result
