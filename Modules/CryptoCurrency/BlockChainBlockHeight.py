#!/usr/bin/env python3


class BlockChainBlockHeight:

    name = "Get Bitcoin Blocks At Height"
    category = "CryptoCurrency"
    description = "Returns the details of all bitcoin blocks at the specified height."
    originTypes = {'Phrase'}
    resultTypes = {'BTC Block'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import requests
        import time
        from datetime import datetime
        returnResults = []

        apiEndpoint = 'https://blockchain.info/block-height/'

        for entity in entityJsonList:
            uid = entity['uid']
            try:
                primaryField = int(entity['Phrase'])
            except ValueError:
                continue

            try:
                heightDetails = requests.get(apiEndpoint + str(primaryField)).json()
                if heightDetails.get('error') is not None:
                    continue
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"

            for details in heightDetails['blocks']:
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
                     {uid: {'Resolution': 'Bitcoin Block Address',
                            'Notes': ''}}])

            time.sleep(5)
        return returnResults
