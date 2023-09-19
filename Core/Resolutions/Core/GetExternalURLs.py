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
        import contextlib
        from urllib.parse import urlparse
        from urllib.parse import parse_qs
        from urllib.parse import unquote
        from base64 import b64decode
        from pathlib import Path

        playwrightPath = Path(parameters['Playwright Browsers Directory']) / 'chromium'
        onionRegex = re.compile(r"""^https?://\w{56}\.onion/?(\S(?<!\.))*(\.(\S(?<!\.))*)?$""")
        returnResult = []

        extract_a = '<a> elements' in parameters['Element types to check']
        extract_img = '<img> elements' in parameters['Element types to check']
        extract_link = '<link> elements' in parameters['Element types to check']

        def get_potential_redirect_value(potential_redirect_url: str) -> str:
            parsed_url = urlparse(potential_redirect_url, allow_fragments=False)
            parsed_url_params = parse_qs(parsed_url.query)
            for param, param_value in parsed_url_params.items():
                with contextlib.suppress(Exception):
                    clean_val = unquote(', '.join(param_value))
                    if urlparse(clean_val).scheme:
                        return clean_val
                    clean_val = unquote(b64decode(', '.join(param_value)).decode('UTF-8'))
                    if urlparse(clean_val).scheme:
                        return clean_val
            return ''

        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=playwrightPath)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            externalUrls = {}

            for site in entityJsonList:
                uid = site['uid']
                url = site['URL']
                parsedURL = urlparse(url)
                if not all([parsedURL.scheme, parsedURL.netloc]):
                    continue
                domain = tldextract.extract(url).fqdn

                # Try to load the page a few times, in case of timeouts.
                # I don't think making parts of this async actually helps in this case.
                for _ in range(3):
                    try:
                        page.goto(url, wait_until="networkidle", timeout=10000)

                        ### Youtube
                        with contextlib.suppress(Exception):
                            page.get_by_role("button",
                                             name="Reject the use of cookies and other data for the purposes described").click()
                        with contextlib.suppress(Exception):
                            page.get_by_role("button", name="Show more").click()
                        soupContents = BeautifulSoup(page.content(), 'lxml')

                        if extract_a:
                            linksInAHref = soupContents.find_all('a')
                            for tag in linksInAHref:
                                link = tag.get('href', None)
                                parsedURL = urlparse(link)
                                if all([parsedURL.scheme, parsedURL.netloc]):
                                    if domain in link:
                                        redirectLink = get_potential_redirect_value(link)
                                        if redirectLink:
                                            try:
                                                externalUrls[redirectLink].add(uid)
                                            except KeyError:
                                                externalUrls[redirectLink] = {uid}
                                    else:
                                        newLink = link.split('#')[0].split('?')[0]
                                        try:
                                            externalUrls[newLink].add(uid)
                                        except KeyError:
                                            externalUrls[newLink] = {uid}
                        if extract_img:
                            linksInImgSrc = soupContents.find_all('img')
                            for tag in linksInImgSrc:
                                link = tag.get('src', None)
                                parsedURL = urlparse(link)
                                if all([parsedURL.scheme, parsedURL.netloc]) and domain not in link:
                                    newLink = link.split('#')[0].split('?')[0]
                                    try:
                                        externalUrls[newLink].add(uid)
                                    except KeyError:
                                        externalUrls[newLink] = {uid}

                        if extract_link:
                            linksInLinkHref = soupContents.find_all('link')
                            for tag in linksInLinkHref:
                                link = tag.get('href', None)
                                parsedURL = urlparse(link)
                                if all([parsedURL.scheme, parsedURL.netloc]) and domain not in link:
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
            for urlUid in externalUrls[externalUrl]:
                if len(onionCheck) == 1:
                    returnResult.append([{'Onion URL': externalUrl, 'Entity Type': 'Onion Website'},
                                         {urlUid: {'Resolution': 'External Link', 'Notes': ''}}])
                else:
                    returnResult.append([{'URL': externalUrl, 'Entity Type': 'Website'},
                                         {urlUid: {'Resolution': 'External Link', 'Notes': ''}}])

        return returnResult
