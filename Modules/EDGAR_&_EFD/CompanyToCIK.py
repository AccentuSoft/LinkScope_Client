#!/usr/bin/env python3


class CompanyToCIK:
    # A string that is treated as the name of this resolution.
    name = "Get CIK ID From Company"

    category = "EDGAR Info"

    # A string that describes this resolution.
    description = "Returns Nodes of contact info for websites"

    originTypes = {'Phrase', 'Company'}

    resultTypes = {'Phrase'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import re
        from bs4 import BeautifulSoup
        from playwright.sync_api import sync_playwright, TimeoutError

        returnResults = []
        index_of_child = []
        cikRegex = re.compile(r'CIK=\d{4,10}', re.IGNORECASE)

        with sync_playwright() as p:
            browser = p.firefox.launch()
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0'
            )
            page = context.new_page()
            for entity in entityJsonList:
                page.wait_for_timeout(1000)
                uid = entity['uid']
                search_term = entity[list(entity)[1]]
                pageResolved = False
                for _ in range(3):
                    try:
                        page.goto(f'https://www.sec.gov/cgi-bin/browse-edgar?company={search_term}',
                                  wait_until="networkidle", timeout=10000)
                        pageResolved = True
                        break
                    except TimeoutError:
                        pass
                if not pageResolved:
                    continue

                soup = BeautifulSoup(page.content(), 'lxml')
                cikIDs = cikRegex.findall(soup.get_text())

                links_with_text = []
                for td_element in soup.find_all('td'):
                    if td_element.text:
                        try:
                            text = td_element.text
                            split = text.split('SIC')[0]
                            links_with_text.append(split)
                        except IndexError:
                            links_with_text.append(td_element.text)

                for link in links_with_text:
                    if search_term.lower() in link.lower():
                        index_of_child.append(len(returnResults))
                        returnResults.append([{'Company Name': link,
                                               'Entity Type': 'Company'},
                                              {uid: {'Resolution': 'Edgar Company',
                                                     'Notes': ''}}])
                for code in cikIDs:
                    returnResults.append([{'CIK': code.split('=')[1],
                                           'Entity Type': 'Edgar ID'},
                                          {index_of_child[cikIDs.index(code)]: {'Resolution': 'CIK Edgar ID',
                                                                                'Notes': ''}}])
            page.close()
            browser.close()
        return returnResults
