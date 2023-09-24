#!/usr/bin/env python3


class GetInternalURLs:
    name = "Get Domain Urls"
    category = "Website Information"
    description = "Returns all URLs in a Domain."
    originTypes = {'Website', 'Domain'}
    resultTypes = {'Website'}

    parameters = {'Include Resources': {'description': 'Should the resolution also return links to images and internal '
                                                       'links (i.e. links to resources used by the site)? Note that '
                                                       'doing so will make the resolution take more time to complete.',
                                        'type': 'SingleChoice',
                                        'value': {'Include images and internal links', 'Only consider links to pages'},
                                        'default': 'Only consider links to pages'}}

    def resolution(self, entityJsonList, parameters):
        import tldextract
        from playwright.sync_api import sync_playwright, TimeoutError, Error
        from bs4 import BeautifulSoup
        from pathlib import Path
        import urllib.parse

        playwrightPath = Path(parameters['Playwright Chromium'])
        returnResult = []
        internalUrls = {}

        considerResources = parameters['Include Resources'] != 'Only consider links to pages'

        def handleLink(currentLink, currentUrl, currentDomain):
            if currentLink is None:
                return None
            if currentLink.startswith('//'):
                if currentUrl.endswith('/'):
                    currentUrl = currentUrl[:-1]
                currentLink = currentUrl + currentLink[1:]
            elif currentLink.startswith('/'):
                urlParts = urllib.parse.urlparse(currentUrl)
                currentLink = f'{urlParts.scheme}://{urlParts.netloc}{currentLink}'
            parsedCurrentURL = urllib.parse.urlparse(currentLink)
            if (
                all([parsedCurrentURL.scheme, parsedCurrentURL.netloc])
                and currentDomain in currentLink
            ):
                newLink = currentLink.split('#')[0].split('?')[0]
                if newLink.endswith('/'):
                    newLink = newLink[:-1]
                return newLink

        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=playwrightPath)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/101.0.4951.64 Safari/537.36'
            )
            page = context.new_page()

            for site in entityJsonList:
                uid = site['uid']
                entityType = site['Entity Type']
                if entityType == 'Domain':
                    url = 'http://' + site['Domain Name']
                else:
                    url = site['URL']
                parsedURL = urllib.parse.urlparse(url)
                if not all([parsedURL.scheme, parsedURL.netloc]):
                    continue
                domain = tldextract.extract(url).fqdn

                domainUrls = [url]
                index = 0
                while index < len(domainUrls):
                    url = domainUrls[index]
                    index += 1
                    for _ in range(3):
                        try:
                            page.goto(url, wait_until="networkidle", timeout=10000)
                            soupContents = BeautifulSoup(page.content(), 'lxml')

                            if domain not in page.url:
                                # Handle redirects to other sites
                                try:
                                    internalUrls[page.url].add(uid)
                                except KeyError:
                                    internalUrls[page.url] = {uid}
                                break

                            linksInAHref = soupContents.find_all('a')
                            for tag in linksInAHref:
                                link = tag.get('href', None)
                                handledLink = handleLink(link, url, domain)
                                if handledLink:
                                    try:
                                        internalUrls[handledLink].add(uid)
                                    except KeyError:
                                        internalUrls[handledLink] = {uid}
                                    if handledLink not in domainUrls:
                                        domainUrls.append(handledLink)

                            if considerResources:
                                linksInImgSrc = soupContents.find_all('img')
                                for tag in linksInImgSrc:
                                    link = tag.get('src', None)
                                    handledLink = handleLink(link, url, domain)
                                    if handledLink:
                                        try:
                                            internalUrls[handledLink].add(uid)
                                        except KeyError:
                                            internalUrls[handledLink] = {uid}
                                        if handledLink not in domainUrls:
                                            domainUrls.append(handledLink)

                                linksInLinkHref = soupContents.find_all('link')
                                for tag in linksInLinkHref:
                                    link = tag.get('href', None)
                                    handledLink = handleLink(link, url, domain)
                                    if handledLink:
                                        try:
                                            internalUrls[handledLink].add(uid)
                                        except KeyError:
                                            internalUrls[handledLink] = {uid}
                                        if handledLink not in domainUrls:
                                            domainUrls.append(handledLink)
                            break
                        except TimeoutError:
                            pass
                        except Error:
                            break

            page.close()
            context.close()
            browser.close()

        for internalUrl in internalUrls:
            for urlUid in internalUrls[internalUrl]:
                returnResult.append([{'URL': internalUrl, 'Entity Type': 'Website'},
                                     {urlUid: {'Resolution': 'Internal Link', 'Notes': ''}}])

        return returnResult
