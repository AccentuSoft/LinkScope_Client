#!/usr/bin/env python3

class CompanyToCIK:
    # A string that is treated as the name of this resolution.
    name = "Get CIK ID From Company"

    # A string that describes this resolution.
    description = "Returns Nodes of contact info for websites"

    originTypes = {'Phrase', 'Company'}

    resultTypes = {'Phrase'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import re
        from bs4 import BeautifulSoup
        from selenium import webdriver

        returnResults = []
        index_of_child = []
        cikRegex = re.compile(r'CIK=\d{4,10}', re.IGNORECASE)

        fireFoxOptions = webdriver.FirefoxOptions()
        fireFoxOptions.headless = True
        driver = webdriver.Firefox(options=fireFoxOptions)

        for entity in entityJsonList:
            uid = entity['uid']
            search_term = entity[list(entity)[1]]
            driver.get(
                f'https://www.sec.gov/cgi-bin/browse-edgar?company={search_term}')

            page = driver.page_source
            cikIDs = cikRegex.findall(str(page))

            soup = BeautifulSoup(page, 'html.parser')
            links_with_text = []
            for a in soup.find_all('td'):
                if a.text:
                    try:
                        text = a.text
                        split = text.split('SIC')[0]
                        links_with_text.append(split)
                    except IndexError:
                        links_with_text.append(a.text)

            for link in links_with_text:
                if search_term.lower() in link.lower():
                    index_of_child.append(len(returnResults))
                    returnResults.append([{'Company Name': link,
                                           'Entity Type': 'Company'},
                                          {uid: {'Resolution': 'Edgar Company',
                                                 'Name': 'Edgar Company',
                                                 'Notes': ''}}])
            for code in cikIDs:
                returnResults.append([{'CIK': code.split('=')[1],
                                       'Entity Type': 'Edgar ID'},
                                      {index_of_child[cikIDs.index(code)]: {'Resolution': 'CIK Edgar ID',
                                                                            'Name': 'CIK Edgar ID',
                                                                            'Notes': ''}}])
        return returnResults
