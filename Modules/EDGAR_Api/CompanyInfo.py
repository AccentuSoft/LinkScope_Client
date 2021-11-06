#!/usr/bin/env python3

class CompanyInfo:
    # A string that is treated as the name of this resolution.
    name = "Get Company Info"

    # A string that describes this resolution.
    description = "Returns Nodes containing Company Information"

    originTypes = {'Edgar ID'}

    resultTypes = {'Phrase, SIC, EIN, Address'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import requests
        import time

        headers = {
            'User-Agent': 'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        }

        returnResults = []
        for entity in entityJsonList:
            uid = entity['uid']
            cik = entity['CIK']
            if cik.lower().startswith('cik'):
                cik = cik.split('cik')[1]
            if len(cik) != 10:
                cik = cik.zfill(1)
            search_url = f'https://data.sec.gov/submissions/CIK{cik}.json'
            time.sleep(1)
            r = requests.get(search_url, headers=headers)
            time.sleep(1)
            if r.status_code != 200:
                return []

            data = r.json()

            exchanges = data['exchanges']
            for exchange in exchanges:
                returnResults.append([{'Exchange Name': exchange,
                                       'Entity Type': 'Exchanges'},
                                      {uid: {'Resolution': 'Exchange',
                                             'Name': 'Exchange',
                                             'Notes': ''}}])

            tickers = data['tickers']
            for ticker in tickers:
                returnResults.append([{'Ticker Name': ticker,
                                       'Entity Type': 'Tickers'},
                                      {uid: {'Resolution': 'Exchange',
                                             'Name': 'Exchange',
                                             'Notes': ''}}])

            if data['insiderTransactionForOwnerExists'] == 1:
                returnResults.append([{'Phrase': 'Insider Transaction For Owner Exists',
                                       'Entity Type': 'Phrase'},
                                      {uid: {'Resolution': '',
                                             'Name': '',
                                             'Notes': ''}}])
            else:
                returnResults.append([{'Phrase': 'Insider Transaction For Owner Does Not Exists',
                                       'Entity Type': 'Phrase'},
                                      {uid: {'Resolution': '',
                                             'Name': '',
                                             'Notes': ''}}])

            if data['insiderTransactionForIssuerExists'] == 1:
                returnResults.append([{'Phrase': 'Insider Transaction For Issuer Exists',
                                       'Entity Type': 'Phrase'},
                                      {uid: {'Resolution': '',
                                             'Name': '',
                                             'Notes': ''}}])
            else:
                returnResults.append([{'Phrase': 'Insider Transaction For Issuer Does Not Exists',
                                       'Entity Type': 'Phrase'},
                                      {uid: {'Resolution': '',
                                             'Name': '',
                                             'Notes': ''}}])

            if data['sic'] is not None:
                returnResults.append([{'SIC': str(data['sic']),
                                       'Description': data['sicDescription'],
                                       'Entity Type': 'SIC'},
                                      {uid: {'Resolution': '',
                                             'Name': '',
                                             'Notes': ''}}])
            if data['ein'] is not None:
                returnResults.append([{'EIN': str(data['ein']),
                                       'Entity Type': 'EIN'},
                                      {uid: {'Resolution': '',
                                             'Name': '',
                                             'Notes': ''}}])
            if data['addresses'] is not None:
                returnResults.append([{'Street Address': data['addresses']['mailing']['street1'],
                                       'Postal Code': data['addresses']['mailing']['zipCode'],
                                       'Country': data['addresses']['mailing']['stateOrCountry'],
                                       'Locality': data['addresses']['mailing']['city'],
                                       'Entity Type': 'Address'},
                                      {uid: {'Resolution': '',
                                             'Name': '',
                                             'Notes': ''}}])

            if data['addresses']['mailing']['street1'] != data['addresses']['business']['street1']:
                returnResults.append([{'Street Address': data['addresses']['business']['street1'],
                                       'Postal Code': data['addresses']['business']['zipCode'],
                                       'Country': data['addresses']['business']['stateOrCountry'],
                                       'Locality': data['addresses']['business']['city'],
                                       'Entity Type': 'Address'},
                                      {uid: {'Resolution': '',
                                             'Name': '',
                                             'Notes': ''}}])
        return returnResults
