#!/usr/bin/env python3

class GetN8FForms:
    # A string that is treated as the name of this resolution.
    name = "Get Recent N-8F Forms"

    # A string that describes this resolution.
    description = "Returns Nodes N-8F Forms Websites"

    originTypes = {'Edgar ID'}

    resultTypes = {'Website'}

    parameters = {'Max Results': {'description': 'Please enter the maximum number of results to return.\n'
                                                 'Returns the 5 most recent by default.',
                                  'type': 'String',
                                  'default': '5'}}

    def resolution(self, entityJsonList, parameters):
        import requests
        import time

        from bs4 import BeautifulSoup

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
                         f'={linkNumbers}&type=N-8F'
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
                    if '/Archives/edgar/data/' in anchor and '.htm' in anchor:
                        time.sleep(1)
                        anchor = 'https://www.sec.gov' + anchor
                        returnResults.append([{'URL': anchor,
                                               'Entity Type': 'Website'},
                                              {uid: {'Resolution': 'N-8F Form',
                                                     'Name': 'N-8F Form',
                                                     'Notes': ''}}])
        return returnResults
