#!/usr/bin/env python3


class DorkingMethod:
    # A string that is treated as the name of this resolution.
    name = "Find RSA keys in Github with Dorking (Startpage)"

    # A string that describes this resolution.
    description = "Returns Nodes of github repos containing RSA keys"

    originTypes = {'Phrase'}

    resultTypes = {'Website'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        from bs4 import BeautifulSoup
        from selenium import webdriver

        returnResults = []
        urls = set()

        fireFoxOptions = webdriver.FirefoxOptions()
        fireFoxOptions.headless = True
        driver = webdriver.Firefox(options=fireFoxOptions)

        for entity in entityJsonList:
            uid = entity['uid']
            search_term = entity[list(entity)[1]]

            search_url = 'https://www.startpage.com/do/dsearch?query=' + search_term + '"+site:github.com+-site:gist' \
                                                                                       '.github.com' \
                                                                                       '+-inurl:issues+-inurl:wiki' \
                                                                                       '+-filetype' \
                                                                                       ':markdown+-filetype:md' \
                                                                                       '+"-----BEGIN+RSA' \
                                                                                       '+PRIVATE+KEY-----" '

            driver.get(search_url)
            doc = driver.page_source
            soup = BeautifulSoup(doc, "lxml")  # store the result from the search

            for link in soup.find_all('a'):
                anchor = link.attrs['href'] if 'href' in link.attrs else ''
                if 'github' in anchor and anchor.startswith('http'):
                    urls.add(anchor)

            for url in urls:
                returnResults.append(
                    [{'URL': url,
                      'Entity Type': 'Website'},
                     {uid: {'Resolution': 'RSA Key',
                            'Name': 'RSA Key',
                            'Notes': ''}}])

        return returnResults
