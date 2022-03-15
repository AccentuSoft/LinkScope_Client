#!/usr/bin/env python3

class Get4Forms:
    # A string that is treated as the name of this resolution.
    name = "Get Recent 4 Forms"

    category = "EDGAR Info"

    # A string that describes this resolution.
    description = "Returns Nodes D Forms"

    originTypes = {'Edgar ID'}

    resultTypes = {'Person, Form4'}

    parameters = {'Max Results': {'description': 'Please enter the maximum number of results to return.\n'
                                                 'Returns the 5 most recent by default.',
                                  'type': 'String',
                                  'default': '5'}}

    def resolution(self, entityJsonList, parameters):
        import requests
        import time
        import xmltodict
        import json
        from bs4 import BeautifulSoup
        from ast import literal_eval

        headers = {
            'User-Agent': 'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        }

        try:
            linkNumbers = int(parameters['Max Results'])
        except ValueError:
            return "Invalid integer provided in 'Max Results' parameter"
        if linkNumbers <= 0:
            return []
        returnResults = []
        for entity in entityJsonList:
            archives_set = set()
            uid = entity['uid']
            cik = entity['CIK']
            if cik.lower().startswith('cik'):
                cik = cik.split('cik')[1]
            if len(cik) != 10:
                cik = cik.zfill(10)
            search_url = f'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&owner=include&count' \
                         f'={linkNumbers}&type=4'
            time.sleep(1)
            r = requests.get(search_url, headers=headers)
            if r.status_code != 200:
                return []

            soup = BeautifulSoup(r.text, "lxml")

            for link in soup.find_all('a'):
                # extract link url from the anchor
                anchor = link.attrs['href'] if 'href' in link.attrs else ''
                if '/Archives/edgar/data/' in anchor:
                    anchor = 'https://www.sec.gov' + anchor
                    archives_set.add(anchor)

            for archive in archives_set:
                time.sleep(1)
                r = requests.get(archive, headers=headers)
                soup = BeautifulSoup(r.text, "lxml")
                for link in soup.find_all('a'):
                    # extract link url from the anchor
                    anchor = link.attrs['href'] if 'href' in link.attrs else ''
                    if '/Archives/edgar/data/' in anchor and '.xml' in anchor and 'xslF345X03' not in anchor:
                        time.sleep(1)
                        anchor = 'https://www.sec.gov' + anchor
                        r = requests.get(anchor, headers=headers)
                        data = (json.dumps(xmltodict.parse(r.text))).replace('null', 'None')
                        data = literal_eval(data)
                        # print(data)

                        index_of_child = len(returnResults)
                        try:
                            remarks = data['ownershipDocument']['remarks']
                        except KeyError:
                            remarks = ''
                        name = data['ownershipDocument']['reportingOwner']['reportingOwnerId']['rptOwnerName']
                        returnResults.append([{'Full Name': name,
                                               'Notes': remarks,
                                               'Entity Type': 'Person'},
                                              {uid: {'Resolution': 'Reporting Owner',
                                                     'Notes': ''}}])

                        if type(data['ownershipDocument']['nonDerivativeTable']['nonDerivativeTransaction']) == dict:
                            value = data['ownershipDocument']['nonDerivativeTable']['nonDerivativeTransaction']
                            try:
                                footnote = value['transactionAmounts']['transactionShares']['footnoteId']['@id']
                            except KeyError:
                                footnote = value['transactionAmounts']['transactionShares']['value']
                            try:
                                footnotePerShare = \
                                    value['transactionAmounts']['transactionPricePerShare']['footnoteId']['@id']
                            except KeyError:
                                footnotePerShare = value['transactionAmounts']['transactionPricePerShare']['value']
                            returnResults.append([{'Security Title': name + ': ' + value['securityTitle']['value'] + ' '
                                                                     + value['transactionCoding'][
                                                                         'transactionCode'] + ' ' +
                                                                     data['ownershipDocument']['ownerSignature'][
                                                                         'signatureDate'],
                                                   'Deemed Execution Date': str(value['deemedExecutionDate']),
                                                   'Equity Swap Involved': value['transactionCoding'][
                                                       'equitySwapInvolved'],
                                                   'Transaction Timeliness': str(value['transactionTimeliness']),
                                                   'Transaction Shares': footnote,
                                                   'Transaction Price Per Share': footnotePerShare,
                                                   'Shares Owned Following Transaction':
                                                       value['postTransactionAmounts'][
                                                           'sharesOwnedFollowingTransaction'],
                                                   'Notes': (': '.join(
                                                       map(str, data['ownershipDocument']['footnotes']['footnote']))),
                                                   'Entity Type': 'Form4'},
                                                  {index_of_child: {'Resolution': 'Form 4',
                                                                    'Notes': ''}}])
                        else:

                            for value in data['ownershipDocument']['nonDerivativeTable']['nonDerivativeTransaction']:
                                try:
                                    footnote = value['transactionAmounts']['transactionShares']['footnoteId']['@id']
                                except KeyError:
                                    footnote = value['transactionAmounts']['transactionShares']['value']
                                try:
                                    footnotePerShare = \
                                        value['transactionAmounts']['transactionPricePerShare']['footnoteId']['@id']
                                except KeyError:
                                    footnotePerShare = value['transactionAmounts']['transactionPricePerShare']['value']
                                returnResults.append(
                                    [{'Security Title': name + ': ' + value['securityTitle']['value'] + ' '
                                                        + value['transactionCoding']['transactionCode'] + ' ' +
                                                        data['ownershipDocument']['ownerSignature']['signatureDate'],
                                      'Deemed Execution Date': str(value['deemedExecutionDate']),
                                      'Equity Swap Involved': value['transactionCoding']['equitySwapInvolved'],
                                      'Transaction Timeliness': str(value['transactionTimeliness']),
                                      'Transaction Shares': footnote,
                                      'Transaction Price Per Share': footnotePerShare,
                                      'Shares Owned Following Transaction':
                                          value['postTransactionAmounts']['sharesOwnedFollowingTransaction']['value'],
                                      'Notes': (
                                          ': '.join(map(str, data['ownershipDocument']['footnotes']['footnote']))),
                                      'Entity Type': 'Form4'},
                                     {index_of_child: {'Resolution': 'Form 4',
                                                       'Notes': ''}}])
        return returnResults
