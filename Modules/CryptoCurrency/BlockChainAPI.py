#!/usr/bin/env python3


class BlockChainAPI:
    # A string that is treated as the name of this resolution.
    name = "BlockChainAPI Get Transaction Details"

    category = "CryptoCurrency"

    # A string that describes this resolution.
    description = "Returns Nodes of balance, sent, received info"

    originTypes = {'Crypto Wallet', 'Phrase'}

    resultTypes = {'Currency'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import requests
        import time
        import datetime
        returnResults = []

        for entity in entityJsonList:
            uid = entity['uid']
            search_address = entity[list(entity)[1]]

            try:
                getSentByAddress = requests.get(
                    f'https://blockchain.info/q/getsentbyaddress/{search_address}?confirmations=6')
                if getSentByAddress.status_code == 404:
                    continue
                time.sleep(1)
                getReceivedByAddress = requests.get(
                    f'https://blockchain.info/q/getreceivedbyaddress/{search_address}?confirmations=6')
                time.sleep(1)
                addressBalance = requests.get(
                    f'https://blockchain.info/q/addressbalance/{search_address}?confirmations=6')
                time.sleep(1)
                addressFirstSeen = requests.get(
                    f'https://blockchain.info/q/addressfirstseen/{search_address}?confirmations=6')
                time.sleep(1)
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"

            dateCreated = str(datetime.datetime.fromtimestamp(float(addressFirstSeen.text))).replace(" ", 'T')

            returnResults.append(
                [{'Amount': str(int(getSentByAddress.text) / 100000000),
                  'Currency Type': 'BTC',
                  'Notes': 'sent by address',
                  'Entity Type': 'Currency'},
                 {uid: {'Resolution': 'Sent by address',
                        'Notes': ''}}])
            returnResults.append(
                [{'Amount': str(int(getReceivedByAddress.text) / 100000000),
                  'Currency Type': 'BTC',
                  'Notes': 'received by address',
                  'Entity Type': 'Currency'},
                 {uid: {'Resolution': 'Received by address',
                        'Notes': ''}}])
            returnResults.append(
                [{'Amount': str(int(addressBalance.text) / 100000000),
                  'Currency Type': 'BTC',
                  'Notes': 'address balance',
                  'Entity Type': 'Currency'},
                 {uid: {'Resolution': 'Address balance',
                        'Notes': ''}}])
            returnResults.append(
                [{'Date': str(dateCreated),
                  'Notes': 'first seen date',
                  'Entity Type': 'Date'},
                 {uid: {'Resolution': 'First seen date',
                        'Notes': ''}}])
            return returnResults
