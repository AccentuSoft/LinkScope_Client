#!/usr/bin/env python3


class BlockChainBlockTransactions:

    name = "Get Bitcoin Block Transactions"
    category = "CryptoCurrency"
    description = "Returns the transactions that happened in a particular bitcoin block."
    originTypes = {'BTC Block'}
    resultTypes = {'BTC Transaction'}
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
                details = requests.get(apiEndpoint + primaryField).json()
                if details.get('error') is not None:
                    continue
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"

            blockTransactions = details.get('tx', [])

            for transaction in blockTransactions:
                inputValue = 0
                for transactionInput in transaction.get('inputs', []):
                    inputValue += (int(transactionInput['prev_out']['value']) / 100000000)

                outputValue = 0
                for transactionOutput in transaction.get('out', []):
                    outputValue += (int(transactionOutput['value']) / 100000000)

                timestamp = datetime.utcfromtimestamp(transaction.get('time')).isoformat()

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
                     {uid: {'Resolution': 'Bitcoin Block Address',
                            'Notes': ''}}])

            time.sleep(5)
        return returnResults
