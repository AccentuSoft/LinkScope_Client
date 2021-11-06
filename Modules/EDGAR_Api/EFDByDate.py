#!/usr/bin/env python3

class EFDByDate:
    name = 'Get EFD Reports by Date'
    description = 'Return Nodes Of Websites to Reports'
    originTypes = {'Date'}
    resultTypes = {'Website'}
    parameters = {'Max Results': {'description': 'Please enter the maximum number of results to return.\n'
                                                 'Returns 5 more recent by default',
                                  'type': 'String',
                                  'default': '5'},
                  'From or To': {'description': 'Choose whether the selected entity should be considered as From or '
                                                'To Date',
                                 'type': 'SingleChoice',
                                 'value': {'To', 'From'}},
                  'Date': {'description': 'Please enter the Date remaining after selecting the previous option\n',
                           'type': 'String',
                           'value': ''},
                  'Filer Type': {'description': 'Please enter the Name you want to search for.\n'
                                                'In the format: [First Name] [Last Name].'
                                                'E.g. "Donald Trump" (No quotes)',
                                 'type': 'MultiChoice',
                                 'value': {'Senator',
                                           'Candidate',
                                           'Former Senator',
                                           }},
                  'Report Type': {'description': 'Please select the Report Type you want to search for.',
                                  'type': 'MultiChoice',
                                  'value': {'Annual',
                                            'Periodic Transactions',
                                            'Due Date Extension',
                                            'Blind Trusts',
                                            'Other Documents',
                                            }}}

    def resolution(self, entityJsonList, parameters):
        import time
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from bs4 import BeautifulSoup, SoupStrainer

        returnResults = []
        links = []

        linkNumbers = int(parameters['Max Results'])

        url = 'https://efdsearch.senate.gov/search/'
        fireFoxOptions = webdriver.FirefoxOptions()
        fireFoxOptions.headless = False
        driver = webdriver.Firefox(options=fireFoxOptions)
        for entity in entityJsonList:
            if parameters['From or To'] == 'From':
                date = entity['Date']
                toDate = parameters['Date']
            else:
                toDate = entity['Date']
                date = parameters['Date']
            uid = entity['uid']
            driver.implicitly_wait(1)
            driver.get(url)
            driver.find_element(By.ID, "agree_statement").click()
            # until it loads the page
            time.sleep(1)
            # wait.until(EC.element_to_be_clickable((By.ID, 'reportTypeLabelAnnual')))
            driver.find_element(By.ID, "fromDate").send_keys(date)
            driver.find_element(By.ID, "toDate").send_keys(toDate)
            for filerType in parameters['Filer Type']:
                if filerType == 'Senator':
                    driver.find_element(By.ID, "filerTypeLabelSenator").click()
                elif filerType == 'Candidate':
                    driver.find_element(By.ID, "filerTypeLabelCandidate").click()
                else:
                    driver.find_element(By.ID, "filerTypeLabelFormerSenator").click()

            for filerType in parameters['Report Type']:
                if filerType == 'Annual':
                    driver.find_element(By.ID, "reportTypeLabelAnnual").click()
                elif filerType == 'Periodic Transactions':
                    driver.find_element(By.ID, "reportTypeLabelPtr").click()
                elif filerType == 'Due Date Extension':
                    driver.find_element(By.ID, "reportTypeLabelExtension").click()
                elif filerType == 'Blind Trusts':
                    driver.find_element(By.ID, "reportTypeLabelBlindTrusts").click()
                else:
                    driver.find_element(By.ID, "reportTypeLabelOther").click()
            driver.find_element(By.CLASS_NAME, "form-control").submit()
            time.sleep(1)
            response = driver.page_source
            for link in BeautifulSoup(response, 'html.parser', parse_only=SoupStrainer('a')):
                """if link.has_attr('href') and 'view' in link:
                    link = 'https://efdsearch.senate.gov/search/' + str(link)
                    links.append(link)"""
                anchor = link.attrs['href'] if 'href' in link.attrs else ''
                if 'view' in anchor:
                    anchor = 'https://efdsearch.senate.gov/search/' + anchor
                    links.append(anchor)

            if linkNumbers > len(links):
                linkNumbers = int(len(links))

            for i in range(linkNumbers):
                returnResults.append([{'URL': links[i], 'Entity Type': 'Website'},
                                      {uid: {'Resolution': 'EFD Reports', 'Notes': ''}}])
        driver.quit()
        return returnResults
