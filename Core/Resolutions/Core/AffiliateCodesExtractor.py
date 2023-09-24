#!/usr/bin/env python3

"""
This resolution can, in rare instances, be a bit unreliable - if it finishes immediately, it's possible that not all
links were considered, as the page's javascript may not have completely finished loading.

Also, since as far as I can tell one cannot mute the audio of playwright, if a site that autoplays video / audio
is explored, it is possible that some audio plays while the page is loading and its contents are processed.
"""


class AffiliateCodesExtractor:
    # A string that is treated as the name of this resolution.
    name = "Extract Affiliate Codes"

    category = "Website Tracking"

    # A string that describes this resolution.
    description = "Returns Facebook and Amazon affiliate codes found in websites."

    originTypes = {'Domain', 'Website'}

    resultTypes = {'Phrase'}

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
                                'default': '0'},
                  'Visit External Links': {'description': 'Affiliate codes can be hidden in shortened links, and they '
                                                          'might not be visible unless one visits the site directly. '
                                                          'Visiting external links should result in more affiliate '
                                                          'tags being extracted. Of course, browsing to random pages '
                                                          'is not always safe.\nVisit external links?',
                                           'type': 'SingleChoice',
                                           'value': {'Yes', 'No'}}}

    def resolution(self, entityJsonList, parameters):
        from playwright.sync_api import sync_playwright, TimeoutError, Error
        from bs4 import BeautifulSoup
        from pathlib import Path
        import urllib
        import tldextract
        import re

        playwrightPath = Path(parameters['Playwright Firefox'])
        returnResults = []
        visitExternal = parameters['Visit External Links'] == 'Yes'

        # Numbers less than zero are the same as zero, but we should try to prevent overflows.
        try:
            maxDepth = max(int(parameters['Max Depth']), 0)
        except ValueError:
            return "Invalid value provided for Max Webpages to follow."

        # Sites like youtube replace external links with a redirect link originating
        #   from the site itself. This sort of gets around that.
        redirectRegex = re.compile(r'q=[^\s][^&^#]*', re.IGNORECASE)

        amazonRegex = re.compile(r'tag=[^\s][^&]*', re.IGNORECASE)
        fbRegex = re.compile(r'client_id=\d{4,25}', re.IGNORECASE)
        webullRegex = re.compile(r'inviteCode=[^\s][^&]*', re.IGNORECASE)
        smartpassiveincomeRegex = re.compile(r'affcode=[^\s][^&]*', re.IGNORECASE)
        skillshareRegex = re.compile(r'utm_campaign=[^\s][^&]*', re.IGNORECASE)
        freetradeRegex = re.compile(r'https://freetrade.app.link/[^\s][^?]*', re.IGNORECASE)
        freetradeRegex2 = re.compile(r'https://magic.freetrade.io/join/[^\s][^?^#]*', re.IGNORECASE)

        exploredDepth = set()
        exploredForeign = set()
        alreadyParsed = set()

        def GetAffiliateCodes(currentUID: str, site: str):
            requestUrl = str(urllib.parse.unquote(site))
            if requestUrl not in alreadyParsed:
                alreadyParsed.add(requestUrl)
                for affiliateCode in amazonRegex.findall(requestUrl):
                    returnResults.append([{'Phrase': affiliateCode,
                                           'Entity Type': 'Phrase'},
                                          {currentUID: {'Resolution': 'Amazon Affiliate Code',
                                                        'Notes': ''}}])
                for affiliateCode in fbRegex.findall(requestUrl):
                    returnResults.append([{'Phrase': affiliateCode,
                                           'Entity Type': 'Phrase'},
                                          {currentUID: {'Resolution': 'Facebook Affiliate Code',
                                                        'Notes': ''}}])
                for affiliateCode in webullRegex.findall(requestUrl):
                    returnResults.append([{'Phrase': affiliateCode,
                                           'Entity Type': 'Phrase'},
                                          {currentUID: {'Resolution': 'WeBull Affiliate Code',
                                                        'Notes': ''}}])
                for affiliateCode in smartpassiveincomeRegex.findall(requestUrl):
                    returnResults.append([{'Phrase': affiliateCode,
                                           'Entity Type': 'Phrase'},
                                          {currentUID: {'Resolution': 'SmartPassiveIncome Affiliate Code',
                                                        'Notes': ''}}])
                for affiliateCode in skillshareRegex.findall(requestUrl):
                    returnResults.append([{'Phrase': affiliateCode,
                                           'Entity Type': 'Phrase'},
                                          {currentUID: {'Resolution': 'SkillShare Affiliate Code',
                                                        'Notes': ''}}])
                for affiliateCode in freetradeRegex.findall(requestUrl):
                    returnResults.append([{'Phrase': affiliateCode,
                                           'Entity Type': 'Phrase'},
                                          {currentUID: {'Resolution': 'FreeTrade Affiliate Code',
                                                        'Notes': ''}}])
                for affiliateCode in freetradeRegex2.findall(requestUrl):
                    returnResults.append([{'Phrase': affiliateCode,
                                           'Entity Type': 'Phrase'},
                                          {currentUID: {'Resolution': 'FreeTrade Affiliate Code',
                                                        'Notes': ''}}])

        def extractCodes(currentUID: str, site: str, depth: int):
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
                return

            soupContents = BeautifulSoup(page.content(), 'lxml')

            linksInLinkHref = soupContents.find_all('link')
            for tag in linksInLinkHref:
                newLink = tag.get('href', None)
                if newLink is not None and newLink.startswith('http'):
                    newLink = newLink.split('#')[0]
                    newDepth = depth - 1
                    if domain in newLink and newLink not in exploredDepth and newDepth > 0:
                        exploredDepth.add(newLink)
                        extractCodes(currentUID, newLink, newDepth)

            linksInAHref = soupContents.find_all('a')
            for tag in linksInAHref:
                newLink = tag.get('href', None)
                if newLink is not None and newLink.startswith('http'):
                    newLink = newLink.split('#')[0]
                    newDepth = depth - 1
                    if domain in newLink:
                        redirLinks = redirectRegex.findall(newLink)
                        if 'redirect' in newLink and len(redirLinks) > 0:
                            newLink = str(urllib.parse.unquote(redirLinks[0]))[2:]
                            if newLink not in exploredForeign:
                                exploredForeign.add(newLink)
                                if visitExternal:
                                    for _ in range(3):
                                        try:
                                            page.goto(newLink, wait_until="networkidle", timeout=10000)
                                            GetAffiliateCodes(currentUID, page.url)
                                            break
                                        except TimeoutError:
                                            pass
                                        except Error:
                                            break
                            else:
                                GetAffiliateCodes(currentUID, newLink)
                        else:
                            if newLink not in exploredDepth and newDepth > 0:
                                exploredDepth.add(newLink)
                                extractCodes(currentUID, newLink, newDepth)
                    elif newLink not in exploredForeign:
                        exploredForeign.add(newLink)
                        if visitExternal:
                            for _ in range(3):
                                try:
                                    page.goto(newLink, wait_until="networkidle", timeout=10000)
                                    GetAffiliateCodes(currentUID, page.url)
                                    break
                                except TimeoutError:
                                    pass
                                except Error:
                                    break
                        else:
                            GetAffiliateCodes(currentUID, newLink)

        with sync_playwright() as p:
            browser = p.firefox.launch(executable_path=playwrightPath)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0'
            )
            for entity in entityJsonList:
                uid = entity['uid']
                url = entity.get('URL') if entity.get('Entity Type', '') == 'Website' else entity.get('Domain Name', None)
                if url is None:
                    continue
                if not url.startswith('http://') and not url.startswith('https://'):
                    url = f'http://{url}'
                domain = tldextract.extract(url).fqdn
                extractCodes(uid, url, maxDepth)
            browser.close()
        return returnResults
