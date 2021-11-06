#!/usr/bin/env python3

class EFDByName:
    name = 'Get EFD Reports by Name'
    description = 'Return Nodes Of Websites to Reports'
    originTypes = {'Person'}
    resultTypes = {'Website'}
    parameters = {'Max Results': {'description': 'Please enter the maximum number of results to return.\n'
                                                 'Returns 5 more recent by default',
                                  'type': 'String',
                                  'default': '5'},
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
        fireFoxOptions.headless = True
        driver = webdriver.Firefox(options=fireFoxOptions)
        for entity in entityJsonList:
            firstName = entity['Full Name'].split(' ')[0]
            lastName = entity['Full Name'].split(' ')[1]
            uid = entity['uid']
            driver.implicitly_wait(1)
            driver.get(url)
            driver.find_element(By.ID, "agree_statement").click()
            # until it loads the page
            time.sleep(1)
            # wait.until(EC.element_to_be_clickable((By.ID, 'reportTypeLabelAnnual')))
            driver.find_element(By.ID, "firstName").send_keys(firstName)
            driver.find_element(By.ID, "lastName").send_keys(lastName)
            for filter_type in parameters['Filer Type']:
                if filter_type == 'Senator':
                    driver.find_element(By.ID, "filerTypeLabelSenator").click()
                elif filter_type == 'Candidate':
                    driver.find_element(By.ID, "filerTypeLabelCandidate").click()
                else:
                    driver.find_element(By.ID, "filerTypeLabelFormerSenator").click()

            for report_type in parameters['Report Type']:
                if report_type == 'Annual':
                    driver.find_element(By.ID, "reportTypeLabelAnnual").click()
                elif report_type == 'Periodic Transactions':
                    driver.find_element(By.ID, "reportTypeLabelPtr").click()
                elif report_type == 'Due Date Extension':
                    driver.find_element(By.ID, "reportTypeLabelExtension").click()
                elif report_type == 'Blind Trusts':
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
                                      {uid: {'Resolution': 'EFD Results', 'Notes': ''}}])
        driver.quit()
        return returnResults
