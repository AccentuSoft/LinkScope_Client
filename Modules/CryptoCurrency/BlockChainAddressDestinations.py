#!/usr/bin/env python3


class BlockChainAddressDestinations:

    name = "Get Outbound Transactions for Bitcoin Address"
    category = "CryptoCurrency"
    description = "Returns the Bitcoin transactions where cryptocurrency was sent from this address."
    originTypes = {'BTC Address'}
    resultTypes = {'BTC Transaction'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import requests
        import time
        from datetime import datetime

        returnResults = []

        apiEndpointAddress = 'https://blockchain.info/rawaddr/'

        for entity in entityJsonList:
            uid = entity['uid']
            primaryField = entity['BTC Address']

            try:
                addressDetails = requests.get(apiEndpointAddress + primaryField).json()
                if addressDetails.get('error') is not None:
                    continue
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"

            blockTransactions = addressDetails.get('txs', [])

            for transaction in blockTransactions:
                inputValue = 0
                isInAddr = False
                for transactionInput in transaction.get('inputs', []):
                    inputValue += (int(transactionInput['prev_out']['value']) / 100000000)
                    if transactionInput['prev_out']['addr'] == primaryField:
                        isInAddr = True

                if not isInAddr:
                    continue

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
                     {uid: {'Resolution': 'BTC Transaction',
                            'Notes': ''}}])

            time.sleep(5)

        return returnResults
