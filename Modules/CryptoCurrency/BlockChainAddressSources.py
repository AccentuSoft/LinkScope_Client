#!/usr/bin/env python3


class BlockChainAddressSources:

    name = "Get Inbound Transactions for Bitcoin Address"
    category = "CryptoCurrency"
    description = "Returns the Bitcoin transactions where cryptocurrency was sent to this address."
    originTypes = {'BTC Address'}
    resultTypes = {'BTC Transaction'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import requests
        import time
        from datetime import datetime

        returnResults = []
        returnResultResolutions = {}

        apiEndpointAddress = 'https://blockchain.info/rawaddr/'

        for entity in entityJsonList:
            primaryField = entity['BTC Address']

            try:
                addressDetails = requests.get(apiEndpointAddress + primaryField).json()
                if addressDetails.get('error') is not None:
                    continue
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"

            blockTransactions = addressDetails.get('txs', [])

            for transaction in blockTransactions:
                outputValue = 0
                isOutAddr = False
                for transactionOutput in transaction.get('out', []):
                    outputValue += (int(transactionOutput['value']) / 100000000)
                    if transactionOutput['addr'] == primaryField:
                        isOutAddr = True

                if not isOutAddr:
                    continue

                inputValue = 0
                for transactionInput in transaction.get('inputs', []):
                    inputValue += (int(transactionInput['prev_out']['value']) / 100000000)

                timestamp = datetime.utcfromtimestamp(transaction.get('time')).isoformat()
                returnResultResolutions[len(returnResults)] = {'Resolution': 'BTC Transaction'}

                returnResults.append(
                    [{'Transaction Hash': transaction['hash'],
                      'Input Value (BTC)': str(inputValue),
                      'Output Value (BTC)': str(outputValue),
                      'Fee': str(transaction['fee']),
                      'Number of Inputs': str(transaction['vin_sz']),
                      'Number of Outputs': str(transaction['vout_sz']),
                      'Transaction Index': str(transaction['tx_index']),
                      'Size': str(transaction['size']),
                      'Height': str(transaction['block_height']),
                      'Entity Type': 'BTC Transaction',
                      'Date Created': timestamp},
                     {'^^^': {'Resolution': 'NULL',
                              'Notes': ''}}])

            time.sleep(5)
            returnResults.append([{'BTC Address': primaryField,
                                   'Entity Type': 'BTC Address'},
                                  returnResultResolutions])
            returnResultResolutions = {}
        return returnResults
