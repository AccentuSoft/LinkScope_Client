#!/usr/bin/env python3

class Get3Forms:
    # A string that is treated as the name of this resolution.
    name = "Get Recent 3 Forms"

    category = "EDGAR Info"

    # A string that describes this resolution.
    description = "Returns Nodes 3 Forms"

    originTypes = {'Edgar ID'}

    resultTypes = {'Person, Form3'}

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
                         f'={linkNumbers}&type=3'
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
                    if '/Archives/edgar/data/' in anchor and 'ownership.xml' in anchor and 'xslF345X02' not in anchor:
                        time.sleep(1)
                        anchor = 'https://www.sec.gov' + anchor
                        r = requests.get(anchor, headers=headers)
                        data = (json.dumps(xmltodict.parse(r.text))).replace('null', 'None')
                        data = literal_eval(data)
                        # print(data)

                        name = data['ownershipDocument']['reportingOwner']['reportingOwnerId']['rptOwnerName']
                        remarks = \
                            data['ownershipDocument']['reportingOwner']['reportingOwnerRelationship']['officerTitle']
                        value = data['ownershipDocument']['nonDerivativeTable']['nonDerivativeHolding']
                        index_of_child = len(returnResults)
                        returnResults.append([{'Full Name': name,
                                               'Notes': remarks,
                                               'Entity Type': 'Person'},
                                              {uid: {'Resolution': 'Reporting Owner',
                                                     'Notes': ''}}])

                        if value['ownershipNature']['directOrIndirectOwnership']['value'] == 'I':
                            nature = 'Indirect'
                        else:
                            nature = 'Direct'
                        returnResults.append([{'Security Title': name + ': ' + value['securityTitle']['value'] + ' ' +
                                                                 data['ownershipDocument']['ownerSignature'][
                                                                     'signatureDate'],
                                               'Shares Owned Following Transaction':
                                                   value['postTransactionAmounts']['sharesOwnedFollowingTransaction'][
                                                       'value'],
                                               'Direct Or Indirect Ownership': nature,
                                               'Nature Of Ownership':
                                                   value['ownershipNature']['natureOfOwnership']['value'],
                                               'Notes': '',
                                               'Entity Type': 'Form3'},
                                              {index_of_child: {'Resolution': 'Form 3',
                                                                'Notes': ''}}])

        return returnResults
