#!/usr/bin/python


class NessusExistingScan:
    name = "Existing Nessus Template Scan"
    category = "Nessus"
    description = "Nessus vulnerability scanner"
    originTypes = {'Phrase'}
    resultTypes = {'Finding', 'Port', 'IP Address', 'IPv6 Address', 'Phrase', 'CVE'}
    parameters = {
        'Nessus Base URL': {'description': 'Enter the url where Nessus starts on your computer or company network '
                                           'e.g: https://127.0.0.1:8834/',
                            'type': 'String',
                            'value': '',
                            'default': 'https://127.0.0.1:8834',
                            'global': True},
        'Nessus Username': {'description': 'Enter the username used for Nessus.',
                            'type': 'String',
                            'value': '',
                            'global': True},
        'Nessus Password': {'description': 'Enter the password used for Nessus.',
                            'type': 'String',
                            'value': '',
                            'global': True}
    }

    def resolution(self, entityJsonList, parameters):
        from defusedxml.ElementTree import parse
        from playwright.sync_api import sync_playwright, TimeoutError

        nessusBaseURL = parameters['Nessus Base URL']
        if not nessusBaseURL.endswith('/'):
            nessusBaseURL = nessusBaseURL + "/"
        nessusUsername = parameters['Nessus Username']
        nessusPassword = parameters['Nessus Password']

        return_results = []

        with sync_playwright() as p:
            browser = p.firefox.launch()
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0',
                ignore_https_errors=True,
                accept_downloads=True
            )
            page = context.new_page()

            pageResolved = False
            for _ in range(3):
                try:
                    page.goto(nessusBaseURL, wait_until="networkidle", timeout=10000)
                    page.fill("[placeholder=\"Username\"]", nessusUsername)
                    page.fill("[placeholder=\"Password\"]", nessusPassword)
                    pageResolved = True
                    break
                except TimeoutError:
                    pass
            if not pageResolved:
                return "Could not access Nessus panel website."

            with page.expect_navigation():
                page.click("text=Sign In")

            for entity in entityJsonList:
                reportUID = entity['uid']
                scanName = entity['Phrase']
                page.click("text=All Scans")

                page.fill("[placeholder=\"Search Scans\"]", scanName)
                # Not required, strictly speaking, but doesn't hurt.
                page.press("[placeholder=\"Search Scans\"]", "Enter")
                try:
                    with page.expect_navigation():
                        page.click("text=" + scanName, timeout=10000)
                except TimeoutError:
                    return "Scan name specified does not exist."

                try:
                    page.click("li:has-text(\"Launch\")", timeout=3000)
                except TimeoutError:
                    try:
                        page.click("text=Launch")
                        with page.expect_navigation():
                            page.click("text=Default")
                    except TimeoutError:
                        return "Scan specified is already running."

                while True:
                    try:
                        page.click("text=Export")
                        break
                    except TimeoutError:
                        page.wait_for_timeout(5000)
                with page.expect_download() as download_info:
                    page.click("li:has-text(\"Nessus\")")
                download = download_info.value

                root = parse(str(download.path()), forbid_dtd=True, forbid_entities=True,
                             forbid_external=True).getroot()
                report = root.find('Report')

                if report is None:
                    return "Report was not properly generated for the scan."

                hostAddress = ""
                for reportHost in report:
                    childIndex = len(return_results)
                    for tag in reportHost.find('HostProperties'):
                        if tag.attrib['name'] == "host-ip":
                            hostAddress = tag.text
                            if ":" in hostAddress:
                                return_results.append([{
                                    'IPv6 Address': hostAddress,
                                    'Entity Type': 'IPv6 Address'},
                                    {reportUID: {'Resolution': 'Nessus Scan', 'Notes': ''}}])
                            else:
                                return_results.append([{
                                    'IP Address': hostAddress,
                                    'Entity Type': 'IP Address'},
                                    {reportUID: {'Resolution': 'Nessus Scan', 'Notes': ''}}])
                    for reportItem in reportHost.findall('ReportItem'):
                        if reportItem.attrib['port'] == '0':
                            cvssScore = reportItem.find('cvss_base_score').text \
                                if reportItem.find('cvss_base_score') is not None else "0"
                            cvssVector = reportItem.find('cvss_vector').text \
                                if reportItem.find('cvss_vector') is not None else "N/A"
                            return_results.append([{
                                'Issue Synopsis': reportItem.find('synopsis').text,
                                'Solution': reportItem.find('solution').text,
                                'CVSS2 Score': cvssScore,
                                'CVSS2 Vector': cvssVector,
                                'Entity Type': 'Finding',
                                'Notes': reportItem.find('plugin_output').text
                                if reportItem.find('plugin_output') is not None else ""},
                                {childIndex: {'Resolution': 'Nessus Scan', 'Notes': ''}}])

                            riskFactor = reportItem.find('risk_factor').text

                            return_results.append([{
                                'Phrase': "Risk Factor: " + riskFactor,
                                'Entity Type': 'Phrase'},
                                {len(return_results) - 1: {'Resolution': 'Nessus Scan', 'Notes': ''}}])

                            cve = reportItem.find('cve').text if reportItem.find('cve') is not None else ""

                            if cve != "":
                                return_results.append([{
                                    'CVE': cve,
                                    'Entity Type': 'CVE'},
                                    {len(return_results) - 1: {'Resolution': 'Nessus Scan', 'Notes': ''}}])

                        else:
                            return_results.append([{
                                'Port': hostAddress + ":" + reportItem.attrib['port'] + ":" + reportItem.attrib[
                                    'protocol'],
                                'Entity Type': 'Port'},
                                {childIndex: {'Resolution': 'Nessus Scan', 'Notes': ''}}])

                            cvssScore = reportItem.find('cvss_base_score').text \
                                if reportItem.find('cvss_base_score') is not None else "0"
                            cvssVector = reportItem.find('cvss_vector').text \
                                if reportItem.find('cvss_vector') is not None else "N/A"
                            return_results.append([{
                                'Issue Synopsis': reportItem.find('synopsis').text,
                                'Solution': reportItem.find('solution').text,
                                'CVSS2 Score': cvssScore,
                                'CVSS2 Vector': cvssVector,
                                'Entity Type': 'Finding',
                                'Notes': reportItem.find('plugin_output').text
                                if reportItem.find('plugin_output') is not None else ""},
                                {len(return_results) - 1: {'Resolution': 'Nessus Scan', 'Notes': ''}}])

                            riskFactor = reportItem.find('risk_factor').text

                            return_results.append([{
                                'Phrase': "Risk Factor: " + riskFactor,
                                'Entity Type': 'Phrase'},
                                {len(return_results) - 1: {'Resolution': 'Nessus Scan', 'Notes': ''}}])

                            cve = reportItem.find('cve').text if reportItem.find('cve') is not None else ""

                            if cve != "":
                                return_results.append([{
                                    'CVE': cve,
                                    'Entity Type': 'CVE'},
                                    {len(return_results) - 1: {'Resolution': 'Nessus Scan', 'Notes': ''}}])
                download.delete()

            page.close()
            browser.close()
        return return_results
