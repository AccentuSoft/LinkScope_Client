class PhoneNumbersExtractor:
    # A string that is treated as the name of this resolution.
    name = "Get Phone Numbers In Domain"

    # A string that describes this resolution.
    description = "Returns Nodes of contact info for websites"

    originTypes = {'Domain'}

    resultTypes = {'Phrase'}

    parameters = {'Max Webpages to Follow': {'description': 'Please enter the maximum number of webpages to follow. '
                                                            'Default number 20. The greater the number the longer the '
                                                            'resolution takes to complete. '
                                                            'Enter "0" (no quotes) to use the default value.',
                                             'type': 'String',
                                             'value': '0'}}

    def resolution(self, entityJsonList, parameters):
        import requests.exceptions
        import tldextract
        from selenium import webdriver
        from bs4 import BeautifulSoup

        returnResults = []
        max_urls = int(parameters['Max Webpages to Follow'])
        if max_urls == 0:
            max_urls = 20

        phoneNumbers = set()

        fireFoxOptions = webdriver.FirefoxOptions()
        fireFoxOptions.headless = True
        driver = webdriver.Firefox(options=fireFoxOptions)

        for entity in entityJsonList:
            uid = entity['uid']

            primaryField = entity[list(entity)[1]]

            if primaryField.startswith('http://') or primaryField.startswith('https://'):
                url = primaryField
            else:
                url = 'https://' + primaryField

            # a queue of urls to be crawled next
            new_urls = {url}

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
                       requests.exceptions.InvalidSchema):
                    # add broken urls to it’s own set, then continue
                    broken_urls.add(poundlessUrl)
                    continue

                for link in soup.find_all('a'):
                    # extract link url from the anchor
                    anchor = link.attrs['href'] if 'href' in link.attrs else ''
                    if anchor.startswith('tel:'):
                        phoneNumbers.add(anchor)
                    if anchor.startswith('/'):
                        local_link = base_url + anchor
                        local_link = local_link.split('#')[0]
                        local_urls.add(local_link)
                        if local_link not in processed_urls and base_url in local_link:
                            new_urls.add(local_link)
                    elif strip_base in anchor:
                        anchor = anchor.split('#')[0]
                        local_urls.add(anchor)
                        if anchor not in processed_urls and base_url in anchor:
                            new_urls.add(anchor)
                    elif not anchor.startswith('http'):
                        local_link = path + anchor
                        local_link = local_link.split('#')[0]
                        local_urls.add(local_link)
                        if local_link not in processed_urls and base_url in local_link:
                            new_urls.add(local_link)
                    else:
                        foreign_urls.add(anchor)

                if len(processed_urls) > max_urls:
                    break

            for i in phoneNumbers:
                returnResults.append([{'Phone Number': i,
                                       'Entity Type': 'Phone Number'},
                                      {uid: {'Resolution': 'Phone Numbers Found',
                                             'Name': 'Phone Numbers Found', 'Notes': ''}}])
        return returnResults
