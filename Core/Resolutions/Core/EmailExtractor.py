class EmailExtractor:
    # A string that is treated as the name of this resolution.
    name = "Get Emails In Domain"

    # A string that describes this resolution.
    description = "Returns Nodes of contact info for websites"

    originTypes = {'Domain'}

    resultTypes = {'Phrase'}

    parameters = {'Max Webpages to Follow': {'description': 'Please enter the maximum number of webpages to follow.\n'
                                                            'Default number 20. The greater the number the longer the\n'
                                                            'resolution takes to complete.\n'
                                                            'Enter "0" (no quotes) to use the default value.',
                                             'type': 'String',
                                             'default': '0'}}

    def resolution(self, entityJsonList, parameters):
        import requests.exceptions
        import re
        import tldextract
        from email_validator import validate_email, caching_resolver, EmailNotValidError
        from selenium import webdriver
        from selenium.common.exceptions import SessionNotCreatedException
        from bs4 import BeautifulSoup

        try:
            fireFoxOptions = webdriver.FirefoxOptions()
            fireFoxOptions.headless = True
            driver = webdriver.Firefox(options=fireFoxOptions)
        except SessionNotCreatedException:
            return "Please install the latest version of Firefox from the official Firefox website"

        returnResults = []
        max_urls = int(parameters['Max Webpages to Follow'])
        if max_urls == 0:
            max_urls = 20

        emails = set()

        for entity in entityJsonList:
            uid = entity['uid']

            primaryField = entity[list(entity)[1]]

            if primaryField.startswith('http://') or primaryField.startswith('https://'):
                url = primaryField
            else:
                url = 'https://' + primaryField

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

            for lurl in processed_urls:
                driver.get(lurl)
                doc = driver.page_source
                new_emails = set(re.findall(r"[\w.-]+@[\w.-]+", doc, re.IGNORECASE))
                emails.update(new_emails)

            resolver = caching_resolver(timeout=10)

            for mail in emails:
                try:
                    # Validate.
                    valid = validate_email(mail, dns_resolver=resolver)

                    returnResults.append([{'Email Address': valid.email,
                                           'Entity Type': 'Email Address'},
                                          {uid: {'Resolution': 'Email Found', 'Name': 'Emails Found', 'Notes': ''}}])
                except EmailNotValidError as e:
                    # email is not valid, exception message is human-readable
                    returnResults.append([{'Phrase': str(e),
                                           'Entity Type': 'Phrase'},
                                          {uid: {'Resolution': 'Email Found', 'Name': 'Emails Found', 'Notes': ''}}])

        driver.quit()
        return returnResults
