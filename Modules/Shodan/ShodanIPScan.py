#!/usr/bin/env python3


class ShodanIPScan:
    name = "Shodan IP Scan"
    description = "Find information about ip addresses and discovered vulnerabilities"
    originTypes = {'IP Address'}
    resultTypes = {'Shodan Scan'}
    parameters = {'Shodan API Key': {'description': 'Enter your API key under your profile after'
                                                    ' signing up on https://shodan.io/. '
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
        return_result.append([{'Country Name': host['country_name'],
                               'Entity Type': 'Country'},
                              {uid: {'Resolution': 'Shodan IP Country', 'Notes': ''}}])
        return_result.append([{'City Name': host['city'],
                               'Entity Type': 'City'},
                              {uid: {'Resolution': 'Shodan IP City', 'Notes': ''}}])
        if host.get('asn') is not None:
            return_result.append([{'AS Number': 'AS' + host['asn'],
                                   'Entity Type': 'Autonomous System'},
                                  {uid: {'Resolution': 'Shodan IP AS Number', 'Notes': ''}}])
        return_result.append([{'Label': host['ip_str'] + " Location",
                               'Longitude': host['longitude'],
                               'Latitude': host['latitude'],
                               'Entity Type': 'GeoCoordinates'},
                              {uid: {'Resolution': 'Shodan IP GeoCoordinates', 'Notes': ''}}])
        for port in host['ports']:
            return_result.append([{'Port': host['ip_str'] + ":" + str(port),
                                   'Entity Type': 'Port'},
                                  {uid: {'Resolution': 'Shodan IP Ports', 'Notes': ''}}])

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
            if scan == "No":
                try:
                    host = api.host(primary_field)
                except shodan.exception.APIError:
                    return "The API Key provided is Invalid"
                self.parsing(host, return_result, uid)
            elif scan == "Yes":
                try:
                    results = api.scan(primary_field)
                except shodan.exception.APIError:
                    return "The API Key provided is Invalid"
                while results['status'] != "DONE":
                    results = api.scan(primary_field)
                    time.sleep(5)
                    break
                try:
                    host = api.host(primary_field)
                except shodan.exception.APIError:
                    return "The API Key provided is Invalid"
                self.parsing(host, return_result, uid)
        return return_result
