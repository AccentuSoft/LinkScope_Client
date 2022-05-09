#!/usr/bin/env python3


class ShodanIPScan:
    name = "Shodan IP Scan"
    category = "Network Infrastructure"
    description = "Find information about ip addresses and discovered vulnerabilities"
    originTypes = {'IP Address', 'IPv6 Address'}
    resultTypes = {'Operating System', 'Organization', 'Country', 'City', 'Autonomous System', 'GeoCoordinates',
                   'Port', 'Domain', 'CVE', 'Phrase'}
    parameters = {'Shodan API Key': {'description': 'Enter your API key under your profile after '
                                                    'signing up on https://shodan.io/.\n'
                                                    'On the Free tier you will have a rate limit of one request per '
                                                    'second.',
                                     'type': 'String',
                                     'value': '',
                                     'global': True},
                  'Scan': {'description': 'Shodan by default returns cached results from the last time that '
                                          'the IP was scanned. Do you want to use credits to re-scan the IP now?',
                           'type': 'SingleChoice',
                           'value': {'Yes', 'No'}}}

    def parsing(self, host, return_result, uid):
        if host.get('os') is not None:
            return_result.append([{'OS Name': host['os'],
                                   'Entity Type': 'Operating System'},
                                  {uid: {'Resolution': 'Shodan IP OS', 'Notes': ''}}])
        if host.get('org') is not None:
            return_result.append([{'Organization Name': host['org'],
                                   'Entity Type': 'Organization'},
                                  {uid: {'Resolution': 'Shodan IP Organization', 'Notes': ''}}])
        if host.get('isp') is not None:
            return_result.append([{'Company Name': host['isp'],
                                   'Entity Type': 'Company'},
                                  {uid: {'Resolution': 'Shodan IP ISP', 'Notes': ''}}])
        return_result.append([{'Country Name': host['country_name'],
                               'Entity Type': 'Country'},
                              {uid: {'Resolution': 'Shodan IP Country', 'Notes': ''}}])
        return_result.append([{'City Name': host['city'],
                               'Entity Type': 'City'},
                              {uid: {'Resolution': 'Shodan IP City', 'Notes': ''}}])
        longitude = host.get('longitude')
        latitude = host.get('latitude')
        if latitude is not None and longitude is not None:
            return_result.append([{'Label': host['ip_str'] + " Location",
                                   'Longitude': host['longitude'],
                                   'Latitude': host['latitude'],
                                   'Entity Type': 'GeoCoordinates'},
                                  {uid: {'Resolution': 'Shodan IP GeoCoordinates', 'Notes': ''}}])
        if host.get('asn') is not None:
            return_result.append([{'AS Number': 'AS' + host['asn'],
                                   'Entity Type': 'Autonomous System'},
                                  {uid: {'Resolution': 'Shodan IP AS Number', 'Notes': ''}}])

        for port in host['ports']:
            return_result.append([{'Port': host['ip_str'] + ":" + str(port),
                                   'Entity Type': 'Port'},
                                  {uid: {'Resolution': 'Shodan IP Ports', 'Notes': ''}}])
        for hostname in host['hostnames']:
            return_result.append([{'Domain Name': hostname,
                                   'Entity Type': 'Domain'},
                                  {uid: {'Resolution': 'Shodan IP Hostnames', 'Notes': ''}}])

        for domain in host['domains']:
            return_result.append([{'Domain Name': domain,
                                   'Entity Type': 'Domain'},
                                  {uid: {'Resolution': 'Shodan IP Domains', 'Notes': ''}}])

        if host.get('data') is not None:
            for dataItem in host['data']:
                if dataItem.get('vulns') is not None:
                    for vuln in dataItem.get('vulns'):
                        # Cast to strings for safety.
                        summary = str(dataItem['vulns'][vuln].get('summary'))
                        cvss = str(dataItem['vulns'][vuln].get('cvss'))
                        verified = dataItem['vulns'][vuln].get('verified')
                        return_result.append([{'CVE': vuln,
                                               'CVSS Score': cvss,
                                               'Entity Type': 'CVE',
                                               'Notes': summary},
                                              {uid: {'Resolution': 'Shodan IP Vulnerabilities', 'Notes': ''}}])
                        if verified:
                            # This never really happens, as far as I can see.
                            return_result.append([{'Phrase': "Vulnerability Verified",
                                                   'Entity Type': 'Phrase'},
                                                  {len(return_result) - 1: {'Resolution': 'Shodan IP Vulnerabilities',
                                                                            'Notes': ''}}])

    def resolution(self, entityJsonList, parameters):
        import shodan
        import time
        from ipaddress import ip_address

        return_result = []
        api_key = parameters['Shodan API Key'].strip()
        scan = parameters['Scan']
        api = shodan.Shodan(api_key)
        for entity in entityJsonList:
            uid = entity['uid']
            primary_field = entity[list(entity)[1]].strip()
            try:
                ip_address(primary_field)
            except ValueError:
                return "The Entity Provided isn't a valid IP Address"
            if scan == "Yes":
                try:
                    results = api.scan(primary_field)
                except shodan.exception.APIError:
                    return "The API Key provided is invalid, or does not have enough credits."
                scanID = results['id']
                scanStatusQuery = api.scan_status(scanID)
                while scanStatusQuery['status'] != 'DONE':
                    time.sleep(10)
                    scanStatusQuery = api.scan_status(scanID)

            try:
                host = api.host(primary_field)
            except shodan.exception.APIError:
                return "The API Key provided is invalid."
            self.parsing(host, return_result, uid)

        return return_result
