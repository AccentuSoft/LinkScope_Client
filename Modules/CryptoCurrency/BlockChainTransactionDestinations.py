#!/usr/bin/env python3


class BlockChainTransactionDestinations:

    name = "Get Bitcoin Transaction Destinations"
    category = "CryptoCurrency"
    description = "Returns the Bitcoin addresses that received cryptocurrency in the specified transaction."
    originTypes = {'BTC Transaction'}
    resultTypes = {'BTC Address'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import requests
        import time

        returnResults = []

        apiEndpointTransaction = 'https://blockchain.info/rawtx/'
        apiEndpointAddress = 'https://blockchain.info/rawaddr/'

        for entity in entityJsonList:
            uid = entity['uid']
            primaryField = entity['Transaction Hash']

            try:
                transaction = requests.get(apiEndpointTransaction + primaryField).json()
                if transaction.get('error') is not None:
                    continue
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"

            for transactionInput in transaction.get('out', []):
                time.sleep(5)
                inputAddress = transactionInput['addr']
                try:
                    details = requests.get(apiEndpointAddress + inputAddress).json()
                    if details.get('error') is not None:
                        continue
                except requests.exceptions.ConnectionError:
                    return "Please check your internet connection"

                returnResults.append(
                    [{'BTC Address': details['address'],
                      'Total Transactions': str(details['n_tx']),
                      'Unredeemed Transactions': str(details['n_unredeemed']),
                      'Total BTC Received': str(details['total_received'] / 100000000),
                      'Total BTC Sent': str(details['total_sent'] / 100000000),
                      'Current Balance': str(details['final_balance'] / 100000000),
                      'Entity Type': 'BTC Address'},
                     {uid: {'Resolution': 'Bitcoin Transaction',
                            'Notes': ''}}])

            time.sleep(5)
        return returnResults
