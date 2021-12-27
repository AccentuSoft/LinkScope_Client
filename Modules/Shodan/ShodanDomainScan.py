#!/usr/bin/env python3


class ShodanDomainScan:
    name = "Shodan Domain Scan"
    description = "Find information about a particular domain"
    originTypes = {'Domain'}
    resultTypes = {'Domain'}
    parameters = {'Shodan API Key': {'description': 'Enter your Premium API key under your profile after'
                                                    'signing up on https://shodan.io/ for more info on billing '
                                                    'plans:https://account.shodan.io/billing',
                                     'type': 'String',
                                     'value': '',
                                     'global': True}}

    def resolution(self, entityJsonList, parameters):
        import shodan
        import hashlib
        from binascii import hexlify

        return_result = []
        api_key = parameters['Shodan API Key'].strip()
        api = shodan.Shodan(api_key)
        for entity in entityJsonList:
            uid = entity['uid']
            primary_field = entity[list(entity)[1]].lower().strip()
            try:
                results = api.dns.domain_info(
                    domain=primary_field, history=False, page=1)
            except shodan.exception.APIError:
                return "The API Key provided is Invalid"
            for subdomain_dict in results['data']:
                value = subdomain_dict['value']
                index_of_child = len(return_result)
                dns_type = subdomain_dict['type']
                if dns_type == "MX":
                    return_result.append([{'Domain Name': value,
                                           'Entity Type': 'Domain'},
                                          {uid: {'Resolution': 'Shodan Domain MX records', 'Notes': ''}}])
                elif dns_type == "CNAME":
                    return_result.append([{'Domain Name': subdomain_dict['subdomain'] + '.' + primary_field,
                                           'Entity Type': 'Domain'},
                                          {uid: {'Resolution': 'Shodan Domain CNAME records', 'Notes': ''}}])
                    return_result.append([{'Domain Name': value,
                                           'Entity Type': 'Domain'},
                                          {uid: {'Resolution': 'Shodan Domain CNAME', 'Notes': ''}}])
                elif dns_type == "A":
                    return_result.append([{'Domain Name': subdomain_dict['subdomain'] + '.' + primary_field,
                                           'Entity Type': 'Domain'},
                                          {uid: {'Resolution': 'Shodan Domain A records', 'Notes': ''}}])
                    return_result.append([{'IP Address': value,
                                           'Entity Type': 'IP Address'},
                                          {index_of_child: {'Resolution': 'Shodan Domain A records', 'Notes': ''}}])
                elif dns_type == "AAAA":
                    return_result.append([{'IPv6 Address': value,
                                           'Entity Type': 'IPv6 Address'},
                                          {uid: {'Resolution': 'Shodan Domain AAAA records', 'Notes': ''}}])
                    return_result.append([{'Domain Name': subdomain_dict['subdomain'],
                                           'Entity Type': 'Domain'},
                                          {uid: {'Resolution': 'Shodan Domain AAAA records', 'Notes': ''}}])
                elif dns_type == "TXT":
                    # Text records could be massive - do not want them breaking the UI
                    textPrimaryField = hashlib.md5(value.encode())  # nosec
                    return_result.append([{'Phrase': primary_field + ' TXT Record: ' +
                                                     hexlify(textPrimaryField.digest()).decode(),
                                           'Entity Type': 'Phrase',
                                           'Notes': value},
                                          {uid: {'Resolution': 'Shodan Domain TXT records', 'Notes': ''}}])
                elif dns_type == "SOA":
                    return_result.append([{'Domain Name': value,
                                           'Entity Type': 'Domain'},
                                          {uid: {'Resolution': 'Shodan Domain SOA records', 'Notes': ''}}])
                elif dns_type == "PTR":
                    return_result.append([{'Domain Name': subdomain_dict['subdomain'],
                                           'Entity Type': 'Domain'},
                                          {uid: {'Resolution': 'Shodan Domain PTR records', 'Notes': ''}}])
                elif dns_type == "NS":
                    return_result.append([{'Domain Name': value,
                                           'Entity Type': 'Domain'},
                                          {uid: {'Resolution': 'Shodan Domain NS records', 'Notes': ''}}])
            for subdomain in results['subdomains']:
                return_result.append([{'Domain Name': subdomain,
                                       'Entity Type': 'Domain'},
                                      {uid: {'Resolution': 'Shodan Domain Subdomains', 'Notes': ''}}])
        return return_result
