#!/usr/bin/env python3


class IPQualityScore_IP:
    name = "IP Quality Score IP"
    description = "Find information about the location of a given IP Address or Validate an Email Address"
    originTypes = {'IP Address'}
    resultTypes = {'Phrase', 'Autonomous System', 'Geocordinates', 'Organization', 'Country', 'City'}
    parameters = {'IPQualityScore Private Key': {'description': 'Enter your private key under your profile after '
                                                                'signing up on https://ipqualityscore.com. The limit '
                                                                'per month is 5000 lookups.',
                                                 'type': 'String',
                                                 'value': '',
                                                 'global': True}}

    def resolution(self, entityJsonList, parameters):
        import requests
        from requests_futures.sessions import FuturesSession
        from concurrent.futures import as_completed
        import pycountry

        return_result = []
        uidList = []
        primaryFields = []
        futures = []

        private_key = parameters['IPQualityScore Private Key']
        url = "https://ipqualityscore.com/api/json/ip/private_key/primary_field?timeout=7"
        with FuturesSession(max_workers=15) as session:
            for entity in entityJsonList:
                uidList.append(entity['uid'])
                primary_field = entity[list(entity)[1]].strip()
                primaryFields.append(primary_field)
                crafted_url = url.replace("primary_field", primary_field).replace("private_key", private_key)
                futures.append(session.get(crafted_url))
        for future in as_completed(futures):
            uid = uidList[futures.index(future)]
            try:
                response = future.result().json()
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"
            if response['success'] != "True" and response['message'] == "You have insufficient credits to make this " \
                                                                        "query. Please contact IPQualityScore " \
                                                                        " support if this error persists.":
                return "Your account doesn't have sufficient credits to complete this operation."
            else:
                Country_Code = response['country_code']
                # Region = response['region']
                City = response['city']
                # ISP = response['ISP']
                ASN = response['ASN']
                Organization = response['organization']
                latitude = response['latitude']
                longitude = response['longitude']
                fraud_score = f"fraud_score: {response['fraud_score']}\n"
                proxy = f"proxy: {response['proxy']}\n"
                vpn = f"vpn: {response['vpn']}\n"
                tor = f"tor: {response['tor']}\n"
                is_crawler = f"iscrawler {response['is_crawler']}\n"
                active_vpn = f"active vpn: {response['active_vpn']}\n"
                active_tor = f"active tor: {response['active_tor']}\n"
                recent_abuse = f"recent abuse: {response['recent_abuse']}\n"
                bot_status = f"bot status: {response['bot_status']}\n"

                return_result.append([{'AS Number': f"AS{str(ASN)}",
                                       'Entity Type': 'Autonomous System'},
                                      {uid: {'Resolution': 'IPQualityScore AS Number', 'Notes': ''}}])
                return_result.append([{'Organization Name': Organization,
                                       'Entity Type': 'Organization'},
                                      {uid: {'Resolution': 'IPQualityScore IP Organization', 'Notes': ''}}])
                return_result.append([{'Country Name': pycountry.countries.get(alpha_2=Country_Code).name,
                                       'Entity Type': 'Country'},
                                      {uid: {'Resolution': 'IPQualityScore Scan', 'Notes': ''}}])
                return_result.append([{'City Name': City,
                                       'Entity Type': 'City'},
                                      {uid: {'Resolution': 'IPQualityScore IP City Name', 'Notes': ''}}])
                return_result.append([{'Label': str(primary_field) + " Location",
                                       'Latitude': latitude,
                                       'Longitude': longitude,
                                       'Entity Type': 'GeoCoordinates'},
                                      {uid: {'Resolution': 'IPQualityScore IP Geolocation', 'Notes': ''}}])
                return_result.append([{'Phrase': response['request_id'],
                                       'Notes': fraud_score + is_crawler + proxy + vpn + tor + active_vpn + active_tor +
                                                recent_abuse + bot_status,
                                       'Entity Type': 'Phrase'},
                                      {uid: {'Resolution': 'IPQualityScore Scan ID', 'Notes': ''}}])
        return return_result
