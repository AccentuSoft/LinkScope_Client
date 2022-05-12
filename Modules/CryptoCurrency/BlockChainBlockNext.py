#!/usr/bin/env python3


class BlockChainBlockNext:

    name = "Get Next Bitcoin Block"
    category = "CryptoCurrency"
    description = "Returns the details of the next bitcoin block."
    originTypes = {'BTC Block'}
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
            primaryField = entity['Block Address']

            try:
                currDetails = requests.get(apiEndpoint + primaryField).json()
                if currDetails.get('error') is not None:
                    continue
                nextBlockHashList = currDetails.get('next_block')
                # Ignore nonexistent or indeterminate 'next' blocks.
                if nextBlockHashList is None or len(nextBlockHashList) > 1:
                    continue
                time.sleep(5)
                details = requests.get(apiEndpoint + nextBlockHashList[0]).json()
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
                 {uid: {'Resolution': 'Next BTC Block',
                        'Notes': ''}}])

            time.sleep(5)
        return returnResults
