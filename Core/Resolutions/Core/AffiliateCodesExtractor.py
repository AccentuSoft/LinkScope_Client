#!/usr/bin/env python3


class AffiliateCodesExtractor:
    # A string that is treated as the name of this resolution.
    name = "Get Affiliate-Codes from Website"

    # A string that describes this resolution.
    description = "Returns Nodes of facebook and amazon affiliate codes for websites"

    originTypes = {'Domain'}

    resultTypes = {'Phrase'}

    parameters = {'Max Webpages to Follow': {'description': 'Please enter the maximum number of webpages to follow. '
                                                            'Default number 20. The greater the number the longer the '
                                                            'resolution takes to complete. '
                                                            'Enter "0" (no quotes) to use the default value.',
                                             'type': 'String',
                                             'default': '0'}}

    def resolution(self, entityJsonList, parameters):
        import requests.exceptions
        import tldextract
        import re
        from selenium import webdriver
        # from urllib.parse import urlsplit
        # from collections import deque
        from bs4 import BeautifulSoup

        returnResults = []
        max_urls = int(parameters['Max Webpages to Follow'])
        if max_urls == 0:
            max_urls = 20

        fireFoxOptions = webdriver.FirefoxOptions()
        fireFoxOptions.headless = True
        driver = webdriver.Firefox(options=fireFoxOptions)
        # Access requests via the `requests` attribute

        for entity in entityJsonList:
            uid = entity['uid']

            primaryField = entity[list(entity)[1]]

            if primaryField.startswith('http://') or primaryField.startswith('https://'):
                url = primaryField
            else:
                url = 'https://' + primaryField

            trackingSites = ['tag=', 'client_id=']
            AffiliateCode = []
            amazonRegex = re.compile(r'tag=[^\s][^&]*', re.IGNORECASE)
            fbRegex = re.compile(r'client_id=\d{4,25}', re.IGNORECASE)

            # a queue of urls to be crawled next
            new_urls = {url}  # deque([url])

            # a set of urls that we have already processed
            processed_urls = set()

            # a set of domains inside the target website
            local_urls = set()

            # a set of domains outside the target website
            foreign_urls = set()

            # a set of broken urls
            broken_urls = set()

            # process urls one by one until we exhaust the queue
            while len(new_urls):
                # move url from the queue to processed url set
                url = new_urls.pop()

                print('current url', url)

                # print the current url
                poundlessUrl = url.split('#')[0]

                if url in processed_urls:
                    continue

                processed_urls.add(url)

                # TODO: Rework this
                # extract base url to resolve relative links
                parts = tldextract.extract(poundlessUrl)
                if parts.subdomain != '':
                    base = parts.subdomain + '.' + parts.domain + '.' + parts.suffix
                else:
                    base = parts.domain + '.' + parts.suffix
                strip_base = parts.domain + '.' + parts.suffix
                base_url = 'https://' + base

                if base_url != poundlessUrl and base_url in poundlessUrl:
                    paths = poundlessUrl.split(base_url, 1)[1]
                    path = poundlessUrl[:poundlessUrl.rfind('/') + 1] if '/' in paths else poundlessUrl
                else:
                    path = poundlessUrl

                try:
                    response = requests.get(poundlessUrl)
                    if response.status_code == 404:
                        continue
                    elif base not in response.url:
                        foreign_urls.add(response.url)
                        continue
                    soup = BeautifulSoup(response.text, "lxml")
                    if response.status_code == 403:
                        driver.get(poundlessUrl)
                        pageSource = driver.page_source
                        soup = BeautifulSoup(pageSource, "lxml")
                        if base_url not in driver.current_url:
                            foreign_urls.add(driver.current_url)
                            continue

                except(requests.exceptions.MissingSchema, requests.exceptions.ConnectionError,
                       requests.exceptions.InvalidURL,
                       requests.exceptions.InvalidSchema, Exception):
                    # add broken urls to it’s own set, then continue
                    broken_urls.add(poundlessUrl)
                    continue

                for link in soup.find_all('a'):
                    # extract link url from the anchor
                    anchor = link.attrs['href'] if 'href' in link.attrs else ''
                    if anchor.startswith('/'):
                        local_link = base_url + anchor
                        local_link = local_link.split('#')[0]
                        local_urls.add(local_link)
                        if local_link not in processed_urls and local_link.startswith(base_url):
                            new_urls.add(local_link)
                    elif strip_base in anchor:
                        anchor = anchor.split('#')[0]
                        local_urls.add(anchor)
                        if anchor not in processed_urls and anchor.startswith(base_url):
                            new_urls.add(anchor)
                    elif not anchor.startswith('http'):
                        local_link = path + anchor
                        local_link = local_link.split('#')[0]
                        local_urls.add(local_link)
                        if local_link not in processed_urls and local_link.startswith(base_url):
                            new_urls.add(local_link)
                    else:
                        foreign_urls.add(anchor)

                if len(processed_urls) > max_urls:
                    break

                # print('Foreign', foreign_urls)

                # print('Processed', processed_urls)
                # print('Local', local_urls)

            for url in foreign_urls:

                if trackingSites[0] in url:
                    AffiliateCode.append(amazonRegex.findall(str(url))[0])
                elif 'ASIN' in url:
                    AffiliateCode.append(url.split('/')[-1])
                elif trackingSites[1] in url:
                    AffiliateCode.append(fbRegex.findall(str(url))[0])

            codes = set(AffiliateCode)
            # print(codes)

            for i in codes:
                if [ele for ele in trackingSites[0] if (ele in str(i))]:
                    returnResults.append([{'Phrase': i,
                                           'Entity Type': 'Phrase'},
                                          {uid: {'Resolution': 'Amazon Affiliate ID',
                                                 'Notes': ''}}])
                else:
                    returnResults.append([{'Phrase': i,
                                           'Entity Type': 'Phrase'},
                                          {uid: {'Resolution': 'Facebook Affiliate ID',
                                                 'Notes': ''}}])
            # print(broken_urls)
            print(foreign_urls)
            print(AffiliateCode)
        return returnResults
