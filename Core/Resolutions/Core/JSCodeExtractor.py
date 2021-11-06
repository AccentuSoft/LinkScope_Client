#!/usr/bin/env python3


class JSCodeExtractor:
    # A string that is treated as the name of this resolution.
    name = "Get Tracking Codes"

    # A string that describes this resolution.
    description = "Returns Nodes of 'ca-pub', 'ua' and 'gtm' tracking codes for domains."

    originTypes = {'Domain'}

    resultTypes = {'Phrase'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):

        def GetTrackingCodes(domain):
            import re
            from seleniumwire import webdriver

            Identifiers = []
            uaIDs = []
            uaRegex = re.compile(r'\bUA-\d{4,10}-\d{1,4}\b', re.IGNORECASE)
            pubRegex = re.compile(r'\bca-pub-\d{1,16}\b', re.IGNORECASE)
            gtmRegex = re.compile(r'\bGTM-[A-Z0-9]{1,7}\b', re.IGNORECASE)
            gRegex = re.compile(r'\bG-[A-Z0-9]{1,15}\b', re.IGNORECASE)
            trackingSites = ['client=ca-pub', 'id=UA', 'id=GTM', 'id=G']

            fireFoxOptions = webdriver.FirefoxOptions()
            fireFoxOptions.headless = True
            driver = webdriver.Firefox(options=fireFoxOptions)
            # Access requests via the `requests` attribute
            driver.get(domain)
            for request in driver.requests:
                requestUrl = str(request.url)
                if [ele for ele in trackingSites if (ele in requestUrl)]:
                    for uaRegexMatch in uaRegex.findall(str(requestUrl)):
                        uaIDs.append(uaRegexMatch)
                    for pubRegexMatch in pubRegex.findall(str(requestUrl)):
                        Identifiers.append(pubRegexMatch)
                    for gtmRegexMatch in gtmRegex.findall(str(requestUrl)):
                        Identifiers.append(gtmRegexMatch)
                    for gRegexMatch in gRegex.findall(str(requestUrl)):
                        Identifiers.append(gRegexMatch)
            for ua in list(set(uaIDs)):
                Identifiers.append(''.join(ua.split('-')[:-1]))
            driver.quit()
            return list(set(Identifiers))

        returnResults = []
        for entity in entityJsonList:
            uid = entity['uid']
            if entity[list(entity)[1]].startswith('http://') or entity[list(entity)[1]].startswith('https://'):
                url = entity[list(entity)[1]]
            else:
                url = 'http://' + entity[list(entity)[1]]
            IDs = GetTrackingCodes(url)

            for i in IDs:
                returnResults.append([{'Phrase': i,
                                       'Entity Type': 'Phrase'},
                                      {uid: {'Resolution': 'Tracker ID',
                                             'Name': 'Tracker ID',
                                             'Notes': ''}}])

        return returnResults
