#!/usr/bin/env python3


class ToCryptoWallet:
    name = "BTC Address To Crypto Wallet"
    category = "CryptoCurrency"
    description = "Convert BTC Address entities to Crypto Wallet entities."
    originTypes = {'BTC Address'}
    resultTypes = {'Crypto Wallet'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):

        returnResults = []

        for entity in entityJsonList:
            primaryField = entity['BTC Address']
            returnResults.append([{'Wallet Address': primaryField,
                                   'Currency Name': 'Bitcoin',
                                   'Entity Type': 'Crypto Wallet'},
                                  {entity['uid']: {'Resolution': 'To Crypto Wallet',
                                                   'Notes': ''}}])

        return returnResults
