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
        from bs4 import BeautifulSoup
        from playwright.sync_api import sync_playwright, TimeoutError, Error

        returnResults = []

        with sync_playwright() as p:
            browser = p.firefox.launch()
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080}
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
                    except Error:
                        break
                if not pageResolved:
                    continue

                soup = BeautifulSoup(page.content(), 'lxml')

                count = 0
                temp = None
                for td_element in soup.find_all('td'):
                    if td_element.text:
                        text = td_element.text
                        splitText = text.split('SIC')[0]
                        if count == 0:
                            temp = [{'CIK': splitText,
                                     'Entity Type': 'Edgar ID'},
                                    {len(returnResults): {'Resolution': 'CIK Edgar ID',
                                                          'Notes': ''}}]
                        elif count == 1:
                            returnResults.append([{'Company Name': splitText,
                                                   'Entity Type': 'Company'},
                                                  {uid: {'Resolution': 'Edgar Company',
                                                         'Notes': ''}}])
                            returnResults.append(temp)
                        elif count == 2:
                            returnResults.append([{'Phrase': "State: " + splitText,
                                                   'Entity Type': 'Phrase'},
                                                  {len(returnResults) - 1: {'Resolution': 'Edgar Company State',
                                                                            'Notes': ''}}])
                        count = (count + 1) % 3

            page.close()
            browser.close()
        return returnResults
