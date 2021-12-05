#!/usr/bin/env python3


class IPWhois:
    name = "IPv4 WhoIs Information"
    description = "Find information about the Whois of a given IP Address"
    originTypes = {'IP Address'}
    resultTypes = {'Country', 'Autonomous System', 'Email Address'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        from ipwhois import IPWhois
        from ipaddress import ip_address
        import pycountry

        return_result = []

        for entity in entityJsonList:
            uid = entity['uid']
            primary_field = entity[list(entity)[1]].strip()
            try:
                ip_address(primary_field)
            except ValueError:
                return "The Entity Provided isn't a valid IP Address"
            IPobject = IPWhois(primary_field)
            response = IPobject.lookup_whois()
            return_result.append([{'AS Number': str(response['asn']),
                                   'ASN Cidr': str(response['asn_cidr']),
                                   'Entity Type': 'Autonomous System'},
                                  {uid: {'Resolution': 'IPWhois', 'Notes': ''}}])
            for net in response['nets']:
                if net['country'] is not None:
                    country = pycountry.countries.get(alpha_2=net['country']).name
                    return_result.append([{'Country Name': country,
                                           'Entity Type': 'Country'},
                                          {uid: {'Resolution': 'IPWhois', 'Notes': ''}}])
                if net['name'] is not None:
                    return_result.append([{'Company Name': net['name'],
                                           'Entity Type': 'Company'},
                                          {uid: {'Resolution': 'IPWhois', 'Notes': ''}}])
                if net['emails'] is not None:
                    for email in net['emails']:
                        return_result.append([{'Email Address': email,
                                               'Entity Type': 'Email Address'},
                                              {uid: {'Resolution': 'IPWhois', 'Notes': ''}}])
        return return_result
