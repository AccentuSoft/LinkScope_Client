#!/usr/bin/env python3


class DorkingMethod:
    # A string that is treated as the name of this resolution.
    name = "RSA Keys Startpage Dorking"

    # A string that describes this resolution.
    description = "Returns Nodes of github repos containing RSA keys"

    originTypes = {'Phrase'}

    resultTypes = {'Website'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        from bs4 import BeautifulSoup
        from playwright.sync_api import sync_playwright, TimeoutError

        returnResults = []
        urls = set()

        with sync_playwright() as p:
            browser = p.firefox.launch()
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0'
            )
            page = context.new_page()
            for entity in entityJsonList:
                uid = entity['uid']
                search_term = entity[list(entity)[1]]

                search_url = 'https://www.startpage.com/do/dsearch?query=' + \
                             search_term + '"+site:github.com+-site:gist' \
                                           '.github.com' \
                                           '+-inurl:issues+-inurl:wiki' \
                                           '+-filetype' \
                                           ':markdown+-filetype:md' \
                                           '+"-----BEGIN+RSA' \
                                           '+PRIVATE+KEY-----" '

                pageResolved = False
                for _ in range(3):
                    try:
                        page.goto(search_url, wait_until="networkidle", timeout=10000)
                        pageResolved = True
                        break
                    except TimeoutError:
                        pass
                if not pageResolved:
                    continue
                soup = BeautifulSoup(page.content(), "lxml")  # store the result from the search

                for link in soup.find_all('a'):
                    anchor = link.attrs['href'] if 'href' in link.attrs else ''
                    if 'github' in anchor and anchor.startswith('http') and anchor not in urls:
                        urls.add(anchor)
                        returnResults.append(
                            [{'URL': anchor,
                              'Entity Type': 'Website'},
                             {uid: {'Resolution': 'RSA Key',
                                    'Notes': ''}}])

        return returnResults
