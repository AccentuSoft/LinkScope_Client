#!/usr/bin/env python3


class ShodanSearchCertSerial:
    name = "Shodan Certificate Search"
    category = "Network Infrastructure"
    description = "Search for websites with certificates whose serial numbers match the one in the input website / " \
                  "domain."
    originTypes = {'Website', 'Domain'}
    resultTypes = {'IP Address', 'IPv6 Address', 'GeoCoordinates', 'Country', 'City', 'Operating System', 'Domain',
                   'Autonomous System'}
    parameters = {'Shodan API Key': {'description': 'Enter your API key under your profile after '
                                                    'signing up on https://shodan.io/.\nFor more info on billing '
                                                    'plans: https://account.shodan.io/billing',
                                     'type': 'String',
                                     'value': '',
                                     'globals': True},

                  'Number of results': {'description': 'Enter the maximum number of results you want returned.',
                                        'type': 'String',
                                        'value': '',
                                        'default': '10'}
                  }

    def resolution(self, entityJsonList, parameters):
        import shodan
        import ssl
        import socket

        sslContext = ssl.create_default_context()

        return_result = []
        api_key = parameters['Shodan API Key'].strip()
        try:
            max_results = int(parameters['Number of results'])
        except ValueError:
            return "The value for parameter 'Max Results' is not a valid integer."
        api = shodan.Shodan(api_key)
        for entity in entityJsonList:
            uid = entity['uid']
            entityType = entity['Entity Type']
            if entityType == 'Website':
                primaryField = entity['URL']
                if primaryField.startswith('https'):
                    primaryField = primaryField[8:].split('/')[0]
                elif primaryField.startswith('http'):
                    # Just in case an entity was created for the http version of a site,
                    #   but there is actually a https version of the site.
                    primaryField = primaryField[7:].split('/')[0]
                else:
                    continue
            elif entityType == 'Domain':
                primaryField = entity['Domain Name']
            else:
                continue

            with sslContext.wrap_socket(socket.socket(), server_hostname=primaryField) as s:
                try:
                    s.connect((primaryField, 443))
                    websiteCertificate = s.getpeercert()
                except socket.error:
                    # If there's an error connecting, move on.
                    continue
            serial = websiteCertificate['serialNumber']

            try:
                search = api.search('ssl.cert.serial:"' + serial + '"')
            except shodan.exception.APIError as err:
                if 'No information available' in str(err):
                    return_result.append([{'Phrase': 'No information in Shodan database.',
                                           'Entity Type': 'Phrase'},
                                          {uid: {'Resolution': 'Shodan 404', 'Notes': ''}}])
                    continue
                return "Error: " + str(err)
            for match in search['matches'][:max_results]:
                ipMatch = str(match['ip_str'])
                if match.get('location') is not None:
                    locationDetails = match['location']
                    longitude = locationDetails.get('longitude')
                    latitude = locationDetails.get('latitude')
                    if latitude is not None and longitude is not None:
                        return_result.append([{'Label': ipMatch + " Location",
                                               'Longitude': str(locationDetails['longitude']),
                                               'Latitude': str(locationDetails['latitude']),
                                               'Entity Type': 'GeoCoordinates'},
                                              {uid: {'Resolution': 'Shodan Search GeoCoordinates', 'Notes': ''}}])
                    countryName = locationDetails.get('country_name')
                    if countryName is not None:
                        return_result.append([{'Country Name': countryName,
                                               'Entity Type': 'Country'},
                                              {uid: {'Resolution': 'Shodan Search Country', 'Notes': ''}}])
                    cityName = locationDetails.get('city')
                    if cityName is not None:
                        return_result.append([{'City Name': cityName,
                                               'Entity Type': 'City'},
                                              {uid: {'Resolution': 'Shodan Search City', 'Notes': ''}}])
                if match.get('asn') is not None:
                    return_result.append([{'AS Number': 'AS' + match['asn'],
                                           'Entity Type': 'Autonomous System'},
                                          {uid: {'Resolution': 'Shodan Search AS Number', 'Notes': ''}}])
                if match.get('os') is not None:
                    return_result.append([{'OS Name': match['os'],
                                           'Entity Type': 'Operating System'},
                                          {uid: {'Resolution': 'Shodan Search OS', 'Notes': ''}}])
                for domain in match['domains']:
                    return_result.append([{'Domain Name': domain,
                                           'Entity Type': 'Domain'},
                                          {uid: {'Resolution': 'Shodan Search Domains', 'Notes': ''}}])
                if entityType != 'IP Address' and entityType != 'IPv6 Address':
                    if match.get('ip') is not None:
                        return_result.append([{
                            'IP Address': ipMatch,
                            'Entity Type': 'IP Address'},
                            {uid: {'Resolution': 'Shodan Search IP', 'Notes': ''}}])
                    else:
                        return_result.append([{
                            'IPv6 Address': ipMatch,
                            'Entity Type': 'IPv6 Address'},
                            {uid: {'Resolution': 'Shodan Search IP', 'Notes': ''}}])
        return return_result
