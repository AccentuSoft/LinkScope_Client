#!/usr/bin/env python3

class Get13FForms:
    # A string that is treated as the name of this resolution.
    name = "Get Recent 13F Forms"

    # A string that describes this resolution.
    description = "Returns Nodes 13F Forms"

    originTypes = {'Edgar ID'}

    resultTypes = {'Form13F'}

    parameters = {'Max Results': {'description': 'Please enter the maximum number of results to return.\n'
                                                 'Returns 5 more recent by default',
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

        name = ''
        date = ''

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
                         f'={linkNumbers}&type=13F-HR'
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
                    if '/Archives/edgar/data/' in anchor and 'primary_doc.xml' in anchor \
                            and 'xslFormDX01' not in anchor and 'xslForm13F_X01' not in anchor:
                        time.sleep(1)
                        anchor = 'https://www.sec.gov' + anchor
                        r = requests.get(anchor, headers=headers)
                        data = literal_eval(json.dumps(xmltodict.parse(r.text)))

                        date = data['edgarSubmission']['headerData']['filerInfo']['periodOfReport']
                        name = data['edgarSubmission']['formData']['coverPage']['filingManager']['name']

                    elif '/Archives/edgar/data/' in anchor and 'infotable.xml' in anchor \
                            and 'xslFormDX01' not in anchor and 'xslForm13F_X01' not in anchor:
                        time.sleep(1)
                        anchor = 'https://www.sec.gov' + anchor
                        r = requests.get(anchor, headers=headers)
                        data = literal_eval(json.dumps(xmltodict.parse(r.text)))

                        for d in data['informationTable']['infoTable']:
                            returnResults.append([{'Name Of Issuer': '13F-HR: ' + name + ' ' + d['nameOfIssuer'] + ' '
                                                                     + date,
                                                   'Title Of Class': d['titleOfClass'],
                                                   'CUSIP': d['cusip'],
                                                   'Value': d['value'],
                                                   'Number Of Shares': d['shrsOrPrnAmt']['sshPrnamt'],
                                                   'Ssh Prnamt Type': d['shrsOrPrnAmt']['sshPrnamtType'],
                                                   'Investment Discretion': d['investmentDiscretion'],
                                                   'Notes': '',

                                                   'Entity Type': 'Form13F'},
                                                  {uid: {'Resolution': 'Form13F',
                                                         'Name': 'Form13F',
                                                         'Notes': ''}}])
        return returnResults
