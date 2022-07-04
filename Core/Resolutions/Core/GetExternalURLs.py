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
    category = "Website Information"
    description = "Returns all links to external sites on a website."
    originTypes = {'Website'}
    resultTypes = {'Website', 'Onion Website'}

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
        import tldextract
        from playwright.sync_api import sync_playwright, TimeoutError, Error
        from bs4 import BeautifulSoup
        import re
        import urllib.parse

        onionRegex = re.compile(r"""^https?://\w{56}\.onion/?(\S(?<!\.))*(\.(\S(?<!\.))*)?$""")
        returnResult = []

        extract_a = '<a> elements' in parameters['Element types to check']
        extract_img = '<img> elements' in parameters['Element types to check']
        extract_link = '<link> elements' in parameters['Element types to check']

        # Sites like youtube replace external links with a redirect link originating
        #   from the site itself. This sort of gets around that.
        redirectRegex = re.compile(r'\?.*(q|url)=\S[^&#?]+', re.IGNORECASE)

        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/101.0.4951.64 Safari/537.36'
            )
            page = context.new_page()
            externalUrls = {}

            for site in entityJsonList:
                uid = site['uid']
                url = site['URL']
                parsedURL = urllib.parse.urlparse(url)
                if not all([parsedURL.scheme, parsedURL.netloc]):
                    continue
                domain = tldextract.extract(url).fqdn

                # Try to load the page a few times, in case of timeouts.
                # I don't think making parts of this async actually helps in this case.
                for _ in range(3):
                    try:
                        page.goto(url, wait_until="networkidle", timeout=10000)
                        soupContents = BeautifulSoup(page.content(), 'lxml')

                        if extract_a:
                            linksInAHref = soupContents.find_all('a')
                            for tag in linksInAHref:
                                link = tag.get('href', None)
                                parsedURL = urllib.parse.urlparse(link)
                                if all([parsedURL.scheme, parsedURL.netloc]):
                                    if domain not in link:
                                        newLink = link.split('#')[0].split('?')[0]
                                        try:
                                            externalUrls[newLink].add(uid)
                                        except KeyError:
                                            externalUrls[newLink] = {uid}
                                    else:
                                        redirectLinks = redirectRegex.findall(link)
                                        if 'redirect' in link and len(redirectLinks) > 0:
                                            try:
                                                newLink = str(urllib.parse.unquote(redirectLinks[0]))[2:]
                                                try:
                                                    externalUrls[newLink].add(uid)
                                                except KeyError:
                                                    externalUrls[newLink] = {uid}
                                            except IndexError:
                                                try:
                                                    externalUrls[redirectLinks[0]].add(uid)
                                                except KeyError:
                                                    externalUrls[redirectLinks[0]] = {uid}
                                            except Exception:
                                                pass

                        if extract_img:
                            linksInImgSrc = soupContents.find_all('img')
                            for tag in linksInImgSrc:
                                link = tag.get('src', None)
                                parsedURL = urllib.parse.urlparse(link)
                                if all([parsedURL.scheme, parsedURL.netloc]):
                                    if domain not in link:
                                        newLink = link.split('#')[0].split('?')[0]
                                        try:
                                            externalUrls[newLink].add(uid)
                                        except KeyError:
                                            externalUrls[newLink] = {uid}

                        if extract_link:
                            linksInLinkHref = soupContents.find_all('link')
                            for tag in linksInLinkHref:
                                link = tag.get('href', None)
                                parsedURL = urllib.parse.urlparse(link)
                                if all([parsedURL.scheme, parsedURL.netloc]):
                                    if domain not in link:
                                        newLink = link.split('#')[0].split('?')[0]
                                        try:
                                            externalUrls[newLink].add(uid)
                                        except KeyError:
                                            externalUrls[newLink] = {uid}
                        break
                    except TimeoutError:
                        pass
                    except Error:
                        break

            page.close()
            context.close()
            browser.close()

        for externalUrl in externalUrls:
            onionCheck = onionRegex.findall(externalUrl)
            if len(onionCheck) == 1:
                for urlUid in externalUrls[externalUrl]:
                    returnResult.append([{'Onion URL': externalUrl, 'Entity Type': 'Onion Website'},
                                         {urlUid: {'Resolution': 'External Link', 'Notes': ''}}])
            else:
                for urlUid in externalUrls[externalUrl]:
                    returnResult.append([{'URL': externalUrl, 'Entity Type': 'Website'},
                                         {urlUid: {'Resolution': 'External Link', 'Notes': ''}}])

        return returnResult
