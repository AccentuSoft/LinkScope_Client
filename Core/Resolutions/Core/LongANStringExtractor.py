#!/usr/bin/env python3

"""
Credit to @cyb_detective:
https://medium.com/@cyb_detective/20-regular-expressions-examples-to-search-for-data-related-to-cryptocurrencies-43e31dd4a5dc
"""


class LongANStringExtractor:
    # A string that is treated as the name of this resolution.
    name = "Extract Long Alphanumeric Strings"

    category = "Website Information"

    # A string that describes this resolution.
    description = "Returns patterns matching common cryptocurrency address formats on a website."

    originTypes = {'Domain', 'Website'}

    resultTypes = {'Phrase'}

    parameters = {'Minimum Length': {'description': 'Specify the minimum length an alphanumeric string has to have '
                                                    'to be extracted.',
                                     'type': 'String',
                                     'value': '',
                                     'default': '20'
                                     }}

    def resolution(self, entityJsonList, parameters):
        from playwright.sync_api import sync_playwright, TimeoutError, Error
        from bs4 import BeautifulSoup
        from pathlib import Path
        import re

        playwrightPath = Path(parameters['Playwright Chromium'])
        try:
            minLength = int(parameters['Minimum Length'])
            if minLength < 1:
                raise ValueError('Invalid min length specified.')
        except ValueError:
            return "Invalid Minimum Length specified."

        returnResults = []

        matchPattern = re.compile(r"\b[a-zA-Z0-9_.-]{" + str(minLength) + r",}\b")

        # The software can deduplicate, but handling it here is better.
        allPatterns = set()

        def extractStrings(currentUID: str, site: str):
            page = context.new_page()
            pageResolved = False
            for _ in range(3):
                try:
                    page.goto(site, wait_until="networkidle", timeout=10000)
                    pageResolved = True
                    break
                except TimeoutError:
                    pass
                except Error:
                    break
            if not pageResolved:
                # Last chance for this to work; some pages have issues with the "networkidle" trigger.
                try:
                    page.goto(site, wait_until="load", timeout=10000)
                except Error:
                    return

            soupContents = BeautifulSoup(page.content(), 'lxml')
            # Remove <span> and <noscript> tags.
            while True:
                try:
                    soupContents.noscript.extract()
                except AttributeError:
                    break
            while True:
                try:
                    soupContents.span.extract()
                except AttributeError:
                    break
            siteContent = soupContents.get_text()

            stringMatches = matchPattern.findall(siteContent)
            for potentialMatch in stringMatches:
                if potentialMatch not in allPatterns:
                    allPatterns.add(potentialMatch)
                    returnResults.append([{'Phrase': potentialMatch,
                                           'Entity Type': 'Phrase'},
                                          {currentUID: {'Resolution': 'Long alphanumeric string',
                                                        'Notes': ''}}])

        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=playwrightPath)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/101.0.4951.54 Safari/537.36'
            )
            for entity in entityJsonList:
                uid = entity['uid']
                url = entity.get('URL') if entity.get('Entity Type', '') == 'Website' else \
                    entity.get('Domain Name', None)
                if url is None:
                    continue
                if not url.startswith('http://') and not url.startswith('https://'):
                    url = f'http://{url}'
                extractStrings(uid, url)
            browser.close()

        return returnResults
