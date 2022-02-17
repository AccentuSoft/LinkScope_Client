#!/usr/bin/env python3


class IndicatorsInfo:
    # A string that is treated as the name of this resolution.
    name = "Pulsedive Indicators Lookup"

    # A string that describes this resolution.
    description = "Returns Nodes of Indicators Info"

    originTypes = {'Domain', 'Website', 'IP Address'}

    resultTypes = {'Phrase, Address, Port, Address, Country, City, Domain, IP Address, Company, Email Address, '
                   'Phone Number'}

    parameters = {'Pulsedive API Key': {
        'description': 'Enter your API Key. If you do not have one, the resolution will not return any results.\n'
                       'Standard Free API limits: 30 requests per minute, and 1,000 requests per day.\n'
                       'If you exceed the limits, no results will be returned.\n'
                       'For more information on API premium plans visit:\n'
                       'https://pulsedive.com/about/api',
        'type': 'String',
        'value': '',
        'global': True}}

    def resolution(self, entityJsonList, parameters):
        import requests
        from requests_futures.sessions import FuturesSession
        from concurrent.futures import as_completed

        returnResults = []
        dns_type = []
        whois_type = []
        uidList = []
        futures = []

        api_key = parameters['Pulsedive API Key']

        with FuturesSession(max_workers=15) as session:
            for entity in entityJsonList:
                uidList.append(entity['uid'])
                search_term = entity[list(entity)[1]]
                futures.append(session.get(
                        f'https://pulsedive.com/api/info.php?indicator={search_term}&pretty=1&key={api_key}'))
        data = {}
        for future in as_completed(futures):
            uid = uidList[futures.index(future)]
            response = future.result()
            try:
                if response.status_code == 429:
                    return "You are sending requests above the rate limit"
                if response.status_code == 404:
                    return "No results were retrieved"
                elif response.status_code == 200:
                    data = response.json()
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"

            for indicator in data["riskfactors"]:
                index_of_child = len(returnResults)
                returnResults.append([{'Phrase': indicator['description'],
                                       'Entity Type': 'Phrase'},
                                      {uid: {'Resolution': 'Pulsedive Indicator Scan',
                                             'Notes': ''}}])
                returnResults.append([{'Phrase': 'risk:' + indicator['risk'],
                                       'Entity Type': 'Phrase'},
                                      {index_of_child: {'Resolution': 'Risk',
                                                        'Notes': ''}}])

            for port in data["attributes"]["port"]:
                returnResults.append([{'Port': search_term + ':' + str(port),
                                       'Entity Type': 'Port'},
                                      {uid: {'Resolution': 'Ports Open',
                                             'Notes': ''}}])

            for technology in data["attributes"]["technology"]:
                returnResults.append([{'Phrase': technology,
                                       'Entity Type': 'Phrase'},
                                      {uid: {'Resolution': 'Technologies Used',
                                             'Notes': ''}}])

            index_of_child = len(returnResults)

            if data["properties"]["geo"] is not None:
                if data["properties"]["geo"].get('address') is not None:
                    returnResults.append([{'Street Address': data["properties"]["geo"]['address'],
                                           'Postal Code': data["properties"]["geo"]['zip'],
                                           'Entity Type': 'Address'},
                                          {uid: {'Resolution': 'Address',
                                                 'Notes': ''}}])
                elif data["properties"]["geo"].get('country') is not None:
                    returnResults.append([{'Country Name': data["properties"]["geo"]['country'],
                                           'Entity Type': 'Country'},
                                          {index_of_child: {'Resolution': 'Country',
                                                            'Notes': ''}}])
                elif data["properties"]["geo"].get('city') is not None:
                    returnResults.append([{'City Name': data["properties"]["geo"]['city'],
                                           'Entity Type': 'City'},
                                          {index_of_child: {'Resolution': 'City',
                                                            'Notes': ''}}])

            dns_list = data["properties"]["dns"]
            for key in dns_list.keys():
                dns_type.append(key)

            resultsLen = len(data["properties"]["dns"])
            for i in range(resultsLen):
                index_of_child = len(returnResults)

                if dns_type[i] == "mx":
                    for value in data["properties"]["dns"]['mx']:
                        returnResults.append([{'Domain Name': value,
                                               'Entity Type': 'Domain'},
                                              {uid: {'Resolution': 'MX Record',
                                                     'Notes': ''}}])
                elif dns_type[i] == "a":
                    returnResults.append([{'IP Address': data["properties"]["dns"]["a"],
                                           'Entity Type': 'IP Address'},
                                          {index_of_child: {'Resolution': 'A Record',
                                                            'Notes': ''}}])

                elif dns_type[i] == "txt":
                    for value in data["properties"]["dns"]['txt']:
                        returnResults.append([{'Phrase': value,
                                               'Entity Type': 'Phrase',
                                               'Notes': value},
                                              {uid: {'Resolution': 'TXT Record',
                                                     'Notes': ''}}])
                elif dns_type[i] == "soa":
                    returnResults.append([{'Domain Name': data["properties"]["dns"]['rname'],
                                           'Entity Type': 'Domain'},
                                          {uid: {'Resolution': 'Rname Record',
                                                 'Notes': ''}}])
                    returnResults.append([{'Domain Name': data["properties"]["dns"]['soa'],
                                           'Entity Type': 'Domain'},
                                          {index_of_child: {'Resolution': 'SOA Record',
                                                            'Notes': ''}}])
                elif dns_type[i] == "ns":
                    for value in data["properties"]["dns"]['ns']:
                        returnResults.append([{'Domain Name': value,
                                               'Entity Type': 'Domain'},
                                              {uid: {'Resolution': 'NS Record',
                                                     'Notes': ''}}])

            if data["properties"].get("ssl") is not None:
                returnResults.append([{'Date': data["properties"]["ssl"]['expires'],
                                       'Notes': 'expiration date of ssl certificate',
                                       'Entity Type': 'Date'},
                                      {uid: {'Resolution': 'expiration date of ssl certificate',
                                             'Notes': ''}}])
                returnResults.append([{'Company Name': data["properties"]["ssl"]['org'],
                                       'Notes': 'issuer of certificate',
                                       'Entity Type': 'Company'},
                                      {uid: {'Resolution': 'issuer of certificate',
                                             'Notes': ''}}])

            for key in data["properties"]["whois"].keys():
                whois_type.append(key)
            field = data["properties"]["whois"]
            for kind in whois_type:
                if kind == "registrar":
                    index_of_child = len(returnResults)

                    returnResults.append([{'Company Name': field[kind],
                                           'Entity Type': 'Company'},
                                          {uid: {'Resolution': 'Registrar Company',
                                                 'Notes': ''}}])

                    returnResults.append([{'Phrase': 'registry domain id' + ":" + field["registry domain id"],
                                           'Entity Type': 'Phrase'},
                                          {index_of_child: {'Resolution': 'Registry Domain ID',
                                                            'Notes': ''}}])

                    returnResults.append([{'Phrase': "registrar iana id" + ":" + field["registrar iana id"],
                                           'Entity Type': 'Phrase'},
                                          {index_of_child: {'Resolution': 'Registrar IANA ID',
                                                            'Notes': ''}}])

                    returnResults.append([{'Email Address': field["registrar abuse contact email"],
                                           'Entity Type': 'Email Address'},
                                          {index_of_child: {'Resolution': 'Registrar abuse contact email',
                                                            'Notes': ''}}])

                    returnResults.append([{'Phone Number': field["registrar abuse contact phone"],
                                           'Entity Type': 'Phone Number'},
                                          {index_of_child: {'Resolution': 'Registrar abuse contact phone',
                                                            'Notes': ''}}])
                elif kind == 'admin organization':
                    index_of_child = len(returnResults)

                    returnResults.append([{'Company Name': field[kind],
                                           'Notes': 'admin organization',
                                           'Entity Type': 'Company'},
                                          {uid: {'Resolution': 'Admin Organisation',
                                                 'Notes': ''}}])
                    returnResults.append([{'Email Address': field['admin email'],
                                           'Notes': 'admin email',
                                           'Entity Type': 'Email Address'},
                                          {index_of_child: {'Resolution': 'Admin Email Address',
                                                            'Notes': ''}}])
                    returnResults.append([{'Phone Number': field['admin phone'],
                                           'Notes': 'admin phone',
                                           'Entity Type': 'Phone Number'},
                                          {index_of_child: {'Resolution': 'Admin Phone Number',
                                                            'Notes': ''}}])

        return returnResults
