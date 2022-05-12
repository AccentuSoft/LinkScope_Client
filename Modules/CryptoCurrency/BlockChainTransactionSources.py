#!/usr/bin/env python3


class BlockChainTransactionSources:

    name = "Get Bitcoin Transaction Sources"
    category = "CryptoCurrency"
    description = "Returns the Bitcoin addresses that sent cryptocurrency in the specified transaction."
    originTypes = {'BTC Transaction'}
    resultTypes = {'BTC Address'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import requests
        import time

        returnResults = []
        returnResultResolutions = {}

        apiEndpointTransaction = 'https://blockchain.info/rawtx/'
        apiEndpointAddress = 'https://blockchain.info/rawaddr/'

        for entity in entityJsonList:
            primaryField = entity['Transaction Hash']

            try:
                transaction = requests.get(apiEndpointTransaction + primaryField).json()
                if transaction.get('error') is not None:
                    continue
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"

            for transactionInput in transaction.get('inputs', []):
                time.sleep(5)
                inputAddress = transactionInput['prev_out']['addr']
                try:
                    details = requests.get(apiEndpointAddress + inputAddress).json()
                    if details.get('error') is not None:
                        continue
                except requests.exceptions.ConnectionError:
                    return "Please check your internet connection"

                returnResultResolutions[len(returnResults)] = {'Resolution': 'BTC Transaction'}
                returnResults.append(
                    [{'BTC Address': details['address'],
                      'Total Transactions': str(details['n_tx']),
                      'Unredeemed Transactions': str(details['n_unredeemed']),
                      'Total BTC Received': str(details['total_received'] / 100000000),
                      'Total BTC Sent': str(details['total_sent'] / 100000000),
                      'Current Balance': str(details['final_balance'] / 100000000),
                      'Entity Type': 'BTC Address'},
                     {'^^^': {'Resolution': 'NULL',
                              'Notes': ''}}])

            time.sleep(5)
            # Re-add the source entity so that we can point to it.
            # Only include the primary field, in case the rest of the fields were updated in the meantime.
            returnResults.append([{'Transaction Hash': primaryField,
                                   'Entity Type': 'BTC Transaction'},
                                  returnResultResolutions])
            returnResultResolutions = {}
        return returnResults
