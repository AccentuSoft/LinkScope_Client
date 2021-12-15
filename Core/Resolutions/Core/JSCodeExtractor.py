#!/usr/bin/env python3


class JSCodeExtractor:
    # A string that is treated as the name of this resolution.
    name = "Extract Tracking Codes"

    # A string that describes this resolution.
    description = "Returns Nodes of 'ca-pub', 'ua' and 'gtm' tracking codes for websites and/or domains."

    originTypes = {'Website', 'Domain'}

    resultTypes = {'Phrase'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        from playwright.sync_api import sync_playwright
        import re
        returnResults = []

        uaRegex = re.compile(r'\bUA-\d{4,10}-\d{1,4}\b', re.IGNORECASE)
        pubRegex = re.compile(r'\bca-pub-\d{1,16}\b', re.IGNORECASE)
        gtmRegex = re.compile(r'\bGTM-[A-Z0-9]{1,7}\b', re.IGNORECASE)
        gRegex = re.compile(r'\bG-[A-Z0-9]{1,15}\b', re.IGNORECASE)

        # In the future, if tracking codes from more companies are supported, change this so that resolutions
        #   indicate which company the code is from.
        def GetTrackingCodes(pageUid, requestUrl) -> None:
            trackingCodes = set()
            trackingCodes.update(set(uaRegex.findall(requestUrl)))
            trackingCodes.update(set(pubRegex.findall(requestUrl)))
            trackingCodes.update(set(gtmRegex.findall(requestUrl)))
            trackingCodes.update(set(gRegex.findall(requestUrl)))

            for trackingCode in trackingCodes:
                returnResults.append([{'Phrase': trackingCode,
                                       'Entity Type': 'Phrase'},
                                      {pageUid: {'Resolution': 'Google Tracking Code',
                                                 'Notes': ''}}])

        with sync_playwright() as p:
            browser = p.firefox.launch()
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0'
            )
            for site in entityJsonList:
                uid = site['uid']
                url = site.get('URL') if site.get('URL', None) is not None else site.get('Domain Name', None)
                if url is None:
                    continue
                if not url.startswith('http://') and not url.startswith('https://'):
                    url = 'http://' + url

                page = context.new_page()
                # Subscribe to "request" events.
                page.on("request", lambda request: GetTrackingCodes(uid, request.url))
                page.goto(url)

        return returnResults
