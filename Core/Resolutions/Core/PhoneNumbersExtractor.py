#!/usr/bin/env python3

"""
This extracts only phone numbers that are marked as a 'tel:' hyperlink.
Extraction of other phone numbers is imprecise, as random numbers may be interpreted as valid phone numbers.
"""


class PhoneNumbersExtractor:
    # A string that is treated as the name of this resolution.
    name = "Extract Phone Numbers"

    category = "Website Information"

    # A string that describes this resolution.
    description = "Returns the Phone Numbers present on a website or index page of a domain."

    originTypes = {'Domain', 'Website'}

    resultTypes = {'Phone Number'}

    parameters = {'Max Depth': {'description': 'Each link leading to another website in the same domain can be '
                                               'explored to discover more entities. Each entity discovered after '
                                               'exploring sites linked in the original website or domain is said to '
                                               'have a "depth" value of 1. Entities found from exploring the links on '
                                               'this page would have a "depth" of 2, and so on. A larger value could '
                                               'result in EXPONENTIALLY more time taken to finish the resolution.\n'
                                               'The default value is "0", which means only the provided website, or '
                                               'the index page of the domain provided, is explored.',
                                'type': 'String',
                                'value': '0',
                                'default': '0'}}

    def resolution(self, entityJsonList, parameters):
        from playwright.sync_api import sync_playwright, TimeoutError, Error
        from bs4 import BeautifulSoup
        import tldextract
        import re

        cleanTagsRegex = re.compile(r'<.*?>')
        phoneNumCharsExclusion = re.compile(r'[^ -+()\[\]\d]')

        returnResults = []

        # Numbers less than zero are the same as zero, but we should try to prevent overflows.
        try:
            maxDepth = max(int(parameters['Max Depth']), 0)
        except ValueError:
            return "Invalid value provided for Max Webpages to follow."

        exploredDepth = set()

        def extractTels(currentUID: str, site: str, depth: int):
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

            linksInAHref = soupContents.find_all('a')
            for tag in linksInAHref:
                newLink = tag.get('href', None)
                if newLink is not None:
                    if newLink.startswith('tel:'):
                        returnResults.append([{'Phone Number': newLink[4:],
                                               'Entity Type': 'Phone Number'},
                                              {currentUID: {'Resolution': 'Phone Number Found',
                                                            'Notes': ''}}])
                    elif newLink.startswith('http'):
                        newLink = newLink.split('#')[0]
                        newDepth = depth - 1
                        if domain in newLink and newLink not in exploredDepth and newDepth > 0:
                            exploredDepth.add(newLink)
                            extractTels(currentUID, newLink, newDepth)

            linksInLinkHref = soupContents.find_all('link')
            for tag in linksInLinkHref:
                newLink = tag.get('href', None)
                if newLink is not None:
                    if newLink.startswith('http'):
                        newLink = newLink.split('#')[0]
                        newDepth = depth - 1
                        if domain in newLink and newLink not in exploredDepth and newDepth > 0:
                            exploredDepth.add(newLink)
                            extractTels(currentUID, newLink, newDepth)
            textTags = soupContents.find_all('p')
            for tag in textTags:
                tagContents = tag.text
                cleanTagContentsList = re.sub(cleanTagsRegex, '', tagContents).split('\n')
                for cleanTag in cleanTagContentsList:
                    cleanTag = cleanTag.strip()
                    if not phoneNumCharsExclusion.findall(cleanTag) and len(re.findall(r'\d', cleanTag)) >= 3:
                        returnResults.append([{'Phone Number': cleanTag,
                                               'Entity Type': 'Phone Number'},
                                              {currentUID: {'Resolution': 'Phone Number Found',
                                                            'Notes': ''}}])

        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/101.0.4951.54 Safari/537.36',
            )
            for entity in entityJsonList:
                uid = entity['uid']
                url = entity.get('URL') if entity.get('Entity Type', '') == 'Website' else \
                    entity.get('Domain Name', None)
                if url is None:
                    continue
                if not url.startswith('http://') and not url.startswith('https://'):
                    url = 'http://' + url
                domain = tldextract.extract(url).fqdn
                extractTels(uid, url, maxDepth)
            browser.close()

        return returnResults
