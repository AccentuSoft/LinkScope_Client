#!/usr/bin/env python3


class EtherScanGetBlocksMined:
    name = "EtherScan.io Get Blocks Mined"
    category = "CryptoCurrency"
    description = "EtherScan Blocks Mined from the selected account"
    originTypes = {"Crypto Wallet"}
    resultTypes = {'Crypto Wallet'}
    parameters = {'EtherScan API Key': {'description': "Enter the api key under your profile after signing up at "
                                                       "https://etherscan.io.",
                                        'type': 'String',
                                        'value': '',
                  'global': True}}

    def resolution(self, entityJsonList, parameters):
        import requests
        import time

        return_result = []

        api_key = parameters['EtherScan API Key']

        for entity in entityJsonList:
            uid = entity['uid']
            primary_field = entity['Wallet Address']
            crafted_url = f"https://api.etherscan.io/api?module=account&action=getminedblocks" \
                          f"&address={primary_field}&tag=latest&apikey={api_key}"
            try:
                response = requests.get(crafted_url)
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"
            response = response.json()
            return_result.append([{'Phrase': response['result'],
                                   'Entity Type': 'Phrase'},
                                  {uid: {'Resolution': 'EtherScan.io Blocks Mined', 'Notes': ''}}])
            time.sleep(0.2)

        return return_result
