#!/usr/bin/env python3


class GetWebsiteText:
    # A string that is treated as the name of this resolution.
    name = "Get Website Text"

    category = "Website Information"

    # A string that describes this resolution.
    description = "Returns the text content of the selected websites."

    originTypes = {'Website'}

    resultTypes = {'Phrase'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        from bs4 import BeautifulSoup
        from bs4.element import Comment
        from playwright.sync_api import sync_playwright, TimeoutError, Error
        from urllib.parse import urlparse

        returnResults = []

        def tag_visible(element):
            if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
                return False
            return not isinstance(element, Comment)

        def text_from_html(body):
            soup = BeautifulSoup(body, 'lxml')
            texts = soup.findAll(text=True)
            visible_texts = filter(tag_visible, texts)
            return u" ".join(t.strip() for t in visible_texts if t.strip() != '')

        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/101.0.4951.64 Safari/537.36'
            )
            page = context.new_page()

            for site in entityJsonList:
                uid = site['uid']
                url = site['URL']
                parsedURL = urlparse(url)
                if not all([parsedURL.scheme, parsedURL.netloc]):
                    continue

                # Try to load the page a few times, in case of timeouts.
                # I don't think making parts of this async actually helps in this case.
                for _ in range(3):
                    try:
                        page.goto(url, wait_until="networkidle", timeout=10000)
                        textContent = text_from_html(page.content())
                        returnResults.append([{'Phrase': f'Website Body of: {url}',
                                               'Notes': textContent,
                                               'Entity Type': 'Phrase'},
                                              {uid: {'Resolution': 'Website Body', 'Notes': ''}}])
                        break
                    except TimeoutError:
                        pass
                    except Error:
                        break

        return returnResults
