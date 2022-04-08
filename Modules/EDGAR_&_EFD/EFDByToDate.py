#!/usr/bin/env python3


class EFDByToDate:
    name = 'Get EFD Reports To Date'
    category = "US Senate Financial Info"
    description = 'Get EFD reports ending at the date specified by the input entities.'
    originTypes = {'Date'}
    resultTypes = {'Politically Exposed Person', 'Website'}
    parameters = {'Max Results': {'description': 'Please enter the maximum number of results to return. '
                                                 'Returns the 5 most recent by default.',
                                  'type': 'String',
                                  'default': '5'},
                  'To Date': {'description': 'Records will be collected from the End Date provided by the input '
                                             'entities. NOTE: The End Date is assumed to be in ISO format.\n'
                                             'A Start Date is required to complete the Date constraints. '
                                             'Please input the Start Date for the search in the format mm/dd/yyyy',
                              'type': 'String',
                              'value': ''},
                  'Filer Type': {'description': 'Please select the Office you wish to search records for.',
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
        from datetime import datetime
        from playwright.sync_api import sync_playwright, TimeoutError, Error
        from bs4 import BeautifulSoup, SoupStrainer, Doctype, Tag

        returnResults = []

        try:
            maxResults = int(parameters['Max Results'])
        except ValueError:
            return "Invalid integer provided in 'Max Results' parameter."

        if maxResults <= 0:
            return []

        try:
            date = datetime.strptime(parameters['To Date'], '%m/%d/%Y')
        except ValueError:
            return "Invalid End Date specified."

        url = 'https://efdsearch.senate.gov/search/'

        with sync_playwright() as p:
            browser = p.firefox.launch()
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0'
            )
            page = context.new_page()

            pageResolved = False
            for _ in range(5):
                try:
                    page.goto(url, wait_until="networkidle", timeout=10000)
                    pageResolved = True
                    break
                except TimeoutError:
                    pass
                except Error:
                    break
            if not pageResolved:
                return "Could not access EFD Search website."

            try:
                page.click("text=I understand the prohibitions on obtaining and use of financial disclosure repor")
            except TimeoutError:
                return "The EFD search website is unresponsive."
            except Error:
                return "Connection Error."
            page.wait_for_timeout(1000)

            for entity in entityJsonList:
                try:
                    # Assume ISO format - guessing
                    toDate = datetime.fromisoformat(entity['Date'])
                except ValueError:
                    continue
                if toDate < date:
                    continue
                date = date.strftime('%m/%d/%Y')
                toDate = toDate.strftime('%m/%d/%Y')
                uid = entity['uid']
                page.wait_for_timeout(1000)

                pageResolved = False
                for _ in range(3):
                    try:
                        page.goto(url, wait_until="networkidle", timeout=10000)
                        pageResolved = True
                        break
                    except TimeoutError:
                        pass
                    except Error:
                        break
                if not pageResolved:
                    continue

                try:
                    page.fill("input[name=\"submitted_end_date\"]", toDate)
                    page.fill("input[name=\"submitted_start_date\"]", date)
                    if 'Senator' in parameters['Filer Type']:
                        page.click("label:has-text(\"Senator\")")
                    if 'Candidate' in parameters['Filer Type']:
                        page.click("label:has-text(\"Candidate\")")
                    if 'Former Senator' in parameters['Filer Type']:
                        page.click("label:has-text(\"Former Senator\")")

                    if 'Annual' in parameters['Report Type']:
                        page.click("text=Annual")
                    if 'Periodic Transactions' in parameters['Report Type']:
                        page.click("text=Periodic Transactions")
                    if 'Due Date Extension' in parameters['Report Type']:
                        page.click("text=Due Date Extension")
                    if 'Blind Trusts' in parameters['Report Type']:
                        page.click("text=Blind Trusts")
                    if 'Other Documents' in parameters['Report Type']:
                        page.click("text=Other Documents")

                    page.click("text=Search Reports")

                    entriesInfo = page.locator('#filedReports_info')
                    entriesInfo.wait_for(state='visible')
                    currentFirstIndex = 1
                    currentLastIndex = int(entriesInfo.inner_text().split(" ")[3])
                    lastIndex = int(entriesInfo.inner_text().split(" ")[5])
                    resultCount = 0

                    if lastIndex == 0:
                        continue

                    # Need to click twice to sort by most recent.
                    page.click("text=Date Received/Filed")
                    page.wait_for_timeout(500)
                    page.click("text=Date Received/Filed")
                    page.wait_for_timeout(500)

                    while True:
                        soup = BeautifulSoup(page.content(), 'lxml', parse_only=SoupStrainer('tr'))
                        for record in soup:
                            if isinstance(record, Tag) and record.get('class'):
                                recordFields = record.childGenerator()
                                senateName = next(recordFields).text
                                senateName += " " + next(recordFields).text
                                office = next(recordFields).text
                                report = next(recordFields)
                                reportType = report.text
                                reportLink = next(report.children).get('href')
                                dateCreated = datetime.strptime(next(recordFields).text, '%m/%d/%Y').isoformat()
                                resultCount += 1
                                childIndex = len(returnResults)
                                returnResults.append([{'Full Name': senateName,
                                                       'Office': office,
                                                       'Entity Type': 'Politically Exposed Person'},
                                                      {uid: {'Resolution': 'EFD Reports', 'Notes': ''}}])
                                returnResults.append([{'URL': 'https://efdsearch.senate.gov' + reportLink,
                                                       'Report Type': reportType,
                                                       'Entity Type': 'Website'},
                                                      {childIndex: {'Resolution': 'Filed Disclosure Report',
                                                                    'Notes': '',
                                                                    'Date Created': dateCreated}}])
                                if resultCount == maxResults:
                                    break

                        # Break if we've read enough records, or we ran out of records on this page.
                        if resultCount == maxResults or currentLastIndex == lastIndex:
                            break

                        # We've read all the available records, so we click next.
                        page.click("text=Next")
                        entriesInfo.wait_for(state='visible')
                        while currentFirstIndex == int(entriesInfo.inner_text().split(" ")[1]):
                            page.wait_for_timeout(1000)
                        currentFirstIndex = int(entriesInfo.inner_text().split(" ")[1])
                        currentLastIndex = int(entriesInfo.inner_text().split(" ")[3])
                        lastIndex = int(entriesInfo.inner_text().split(" ")[5])

                except TimeoutError:
                    continue
                except Exception as e:
                    return "Resolution '" + self.name + "' encountered an error: " + str(e)

            page.close()
            browser.close()
        return returnResults
