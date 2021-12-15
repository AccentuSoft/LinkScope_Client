#!/usr/bin/env python3

"""
This resolution can be notoriously hard to get working. Because one cannot get any indication of when the scripts on
a page have finished running, it is possible that some results are missed if one is not extremely careful.

Waiting until network traffic has ended should be the safest way to ensure that all javascript has loaded, and as such,
it would be the most likely point in time where the scripts on the visited page have exposed any useful information
to be gleamed.

Of course, that runs the risk of the operation timing out for whatever reason, or the operation taking a very long
time to complete. It also means that making it async risks that some information is missed due to errors, since
catching them would essentially negate the benefit of doing operations asynchronously.

Tweaks to this script can be made depending on each investigator's workflow.
"""


class GetExternalURLs:
    name = "Get External Urls"
    description = "Returns all links to external sites on a website."
    originTypes = {'Website'}
    resultTypes = {'Website'}

    parameters = {'Element types to check': {'description': 'Select the types of elements to investigate for '
                                                            'external links. Note that "a" elements have the lowest '
                                                            'chance to present false positives, whereas other types '
                                                            'of elements might point to websites that are affiliated '
                                                            'with the input URL in some way, such as content delivery '
                                                            'networks owned by the same entity.',
                                             'type': 'MultiChoice',
                                             'value': {'<a> elements', '<img> elements', '<link> elements'},
                                             'default': ['<a> elements']
                                             }}

    def resolution(self, entityJsonList, parameters):
        import urllib
        from playwright.sync_api import sync_playwright, TimeoutError
        from bs4 import BeautifulSoup
        import re

        returnResult = []

        extract_a = '<a> elements' in parameters['Element types to check']
        extract_img = '<img> elements' in parameters['Element types to check']
        extract_link = '<link> elements' in parameters['Element types to check']

        # Sites like youtube replace external links with a redirect link originating
        #   from the site itself. This sort of gets around that.
        redirectRegex = re.compile(r'q=[^\s][^&^#]*', re.IGNORECASE)

        with sync_playwright() as p:
            browser = p.firefox.launch()
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0'
            )
            allPages = []
            for site in entityJsonList:
                uid = site['uid']
                url = site['URL']
                if url is None:
                    continue
                if not url.startswith('http://') and not url.startswith('https://'):
                    url = 'http://' + url
                domain = ".".join(urllib.parse.urlparse(url).netloc.split('.')[-2:])

                page = context.new_page()
                allPages.append((domain, page, uid))

                # Try to load the page a few times, in case of timeouts.
                # I don't think making parts of this async actually helps in this case.
                for _ in range(3):
                    try:
                        page.goto(url, wait_until="networkidle", timeout=10000)
                        break
                    except TimeoutError:
                        pass
            for urlVisited in allPages:
                externalUrls = set()
                soupContents = BeautifulSoup(urlVisited[1].content(), 'lxml')

                if extract_a:
                    linksInAHref = soupContents.find_all('a')
                    for tag in linksInAHref:
                        link = tag.get('href', None)
                        if link is not None:
                            if link.startswith('http'):
                                if urlVisited[0] not in link:
                                    externalUrls.add(link.split('#')[0])
                                else:
                                    redirLinks = redirectRegex.findall(link)
                                    if 'redirect' in link and len(redirLinks) > 0:
                                        newLink = str(urllib.parse.unquote(redirLinks[0]))[2:]
                                        externalUrls.add(newLink)

                if extract_img:
                    linksInImgSrc = soupContents.find_all('img')
                    for tag in linksInImgSrc:
                        link = tag.get('src', None)
                        if link is not None:
                            if link.startswith('http'):
                                if urlVisited[0] not in link:
                                    externalUrls.add(link.split('#')[0])

                if extract_link:
                    linksInLinkHref = soupContents.find_all('link')
                    for tag in linksInLinkHref:
                        link = tag.get('href', None)
                        if link is not None:
                            if link.startswith('http'):
                                if urlVisited[0] not in link:
                                    externalUrls.add(link.split('#')[0])

                for externalUrl in externalUrls:
                    returnResult.append([{'URL': externalUrl, 'Entity Type': 'Website'},
                                         {urlVisited[2]: {'Resolution': 'External Link', 'Notes': ''}}])
            browser.close()

        return returnResult
