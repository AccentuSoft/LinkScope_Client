#!/usr/bin/env python3


class BlockChainTransaction:

    name = "Get Bitcoin Transaction"
    category = "CryptoCurrency"
    description = "Returns the details of the specified Bitcoin transaction."
    originTypes = {'BTC Transaction', 'Hash', 'Phrase'}
    resultTypes = {'BTC Transaction'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import requests
        import time
        from datetime import datetime
        returnResults = []

        apiEndpoint = 'https://blockchain.info/rawtx/'

        for entity in entityJsonList:
            uid = entity['uid']
            primaryField = entity[list(entity)[1]]

            try:
                transaction = requests.get(apiEndpoint + primaryField).json()
                if transaction.get('error') is not None:
                    continue
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"

            timestamp = datetime.utcfromtimestamp(transaction.get('time')).isoformat()

            inputValue = 0
            for transactionInput in transaction.get('inputs', []):
                inputValue += (int(transactionInput['prev_out']['value']) / 100000000)

            outputValue = 0
            for transactionOutput in transaction.get('out', []):
                outputValue += (int(transactionOutput['value']) / 100000000)

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
                 {uid: {'Resolution': 'Bitcoin Transaction Information',
                        'Notes': ''}}])

            time.sleep(5)
        return returnResults
