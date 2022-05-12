#!/usr/bin/env python3


class BlockChainBlock:

    name = "Get Bitcoin Block Details"
    category = "CryptoCurrency"
    description = "Returns the details of a particular bitcoin block."
    originTypes = {'Hash', 'Phrase', 'BTC Block'}
    resultTypes = {'BTC Block'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import requests
        import time
        from datetime import datetime
        returnResults = []

        apiEndpoint = 'https://blockchain.info/rawblock/'

        for entity in entityJsonList:
            uid = entity['uid']
            primaryField = entity[list(entity)[1]]

            try:
                details = requests.get(apiEndpoint + primaryField).json()
                if details.get('error') is not None:
                    continue
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"

            timestamp = datetime.utcfromtimestamp(details.get('time')).isoformat()

            returnResults.append(
                [{'Block Address': details['hash'],
                  'Previous Block': details['prev_block'],
                  'Merkle Root': details['mrkl_root'],
                  'Relayed By': details['relayed_by'],
                  'Nonce': str(details['nonce']),
                  'Bits': str(details['bits']),
                  'Size': str(details['size']),
                  'Block Index': str(details['block_index']),
                  'Height': str(details['height']),
                  'Main Chain': str(details['main_chain']),
                  'Entity Type': 'BTC Block',
                  'Date Created': timestamp},
                 {uid: {'Resolution': 'Bitcoin Block Details',
                        'Notes': ''}}])

            time.sleep(5)
        return returnResults
