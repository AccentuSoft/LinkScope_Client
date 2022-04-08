#!/usr/bin/env python3


class BigMatch:
    name = "BigMatch Search"
    category = "Secrets & Leaks"
    description = "Find information about a file using https://bigmatch.rev.ng/static/index.html"
    originTypes = {"Image", "Document", "Archive"}
    resultTypes = {'Website'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        from pathlib import Path
        from playwright.sync_api import sync_playwright, TimeoutError, Error
        from bs4 import BeautifulSoup

        return_result = []

        url = "https://bigmatch.rev.ng/static/index.html"
        failString = 'Too many strings in binary?'
        successString = 'Results:'

        with sync_playwright() as p:
            browser = p.firefox.launch()
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0'
            )
            page = context.new_page()

            for entity in entityJsonList:
                uid = entity['uid']
                file_path = Path(parameters['Project Files Directory']) / entity["File Path"]
                file_path = file_path.absolute()
                if not (file_path.exists() and file_path.is_file()):
                    continue
                page.wait_for_timeout(3000)

                for _ in range(3):
                    try:
                        page.goto(url, wait_until="networkidle", timeout=10000)
                        inputLocator = page.locator("input")
                        inputLocator.set_input_files([str(file_path)])
                        page.wait_for_timeout(3000)
                        soup = BeautifulSoup(page.content(), 'lxml')
                        soupText = soup.get_text()
                        while (failString not in soupText) and (successString not in soupText):
                            page.wait_for_timeout(1000)
                            soup = BeautifulSoup(page.content(), 'lxml')
                            soupText = soup.get_text()
                        if failString in soupText:
                            return []
                        for link in soup.find_all('a'):
                            potentialLink = link.get('href', None)
                            if potentialLink is not None:
                                if 'github' in potentialLink:
                                    return_result.append([{'URL': potentialLink, 'Entity Type': 'Website'},
                                                          {uid: {'Resolution': 'BigMatch Github Link', 'Notes': ''}}])

                        break
                    except TimeoutError:
                        pass
                    except Error:
                        break
            page.close()
            browser.close()
        return return_result
