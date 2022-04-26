#!/usr/bin/env python3


class JSCodeExtractor:
    # A string that is treated as the name of this resolution.
    name = "Extract Tracking Codes"

    category = "Website Tracking"

    # A string that describes this resolution.
    description = "Returns Nodes of 'ca-pub', 'ua' and 'gtm' tracking codes for websites and/or domains."

    originTypes = {'Website', 'Domain'}

    resultTypes = {'Phrase'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        from playwright.sync_api import sync_playwright, Error
        import re
        returnResults = []
        requestUrlsParsed = set()

        uaRegex = re.compile(r'\bUA-\d{4,10}-\d{1,4}\b', re.IGNORECASE)
        pubRegex = re.compile(r'\bca-pub-\d{1,16}\b', re.IGNORECASE)
        gtmRegex = re.compile(r'\bGTM-[A-Z\d]{1,7}\b')
        gRegex = re.compile(r'\bG-[A-Z\d]{1,15}\b', re.IGNORECASE)
        qualtricsRegex = re.compile(r'\bQ_(?:Z|S)ID=\w*\b')
        pingdomRegex = re.compile(r'\bpa-[a-fA-F\d]{24}.js\b$')
        mPulseRegex = re.compile(r'\b[A-Z\d]{5}(?:-[A-Z\d]{5}){4}\b')
        contextWebRegex = re.compile(r'\.contextweb\.com.*token=.*')
        facebookRegex = re.compile(r'facebook.com/tr?.*id=\d*')
        googleMapsRegex = re.compile(r'maps\.googleapis\.com/maps/api/js\?.*client=[ a-zA-Z\d-]*')
        marketoRegex = re.compile(r'marketo\.com/rtp-api/v1/rtp.js\?.*aid=[ a-zA-Z\d-]*')
        visualWebsiteOptimizerRegex = re.compile(r'visualwebsiteoptimizer\.com/j\.php\?.*a=\d*')
        optimizeRegex = re.compile(r'googleoptimize\.com/optimize\.js\?.*id=[A-Z\d-]*')
        markMonitorRegex = re.compile(r'\.adsrvr\.org/track/evnt/\?.*adv=[a-zA-Z\d-]*')
        zendeskRegex = re.compile(r'\.zdassets\.com/ekr/snippet\.js\?.*key=[a-zA-Z\d-]*')
        quantServeRegex = re.compile(r'pixel\.quantserve\.com/pixel/.*\.gif\?')

        def GetTrackingCodes(pageUid, requestUrl) -> None:
            if requestUrl not in requestUrlsParsed:
                requestUrlsParsed.add(requestUrl)
                for uaCode in uaRegex.findall(requestUrl):
                    returnResults.append([{'Phrase': uaCode,
                                           'Entity Type': 'Phrase'},
                                          {pageUid: {'Resolution': 'Google UA Tracking Code',
                                                     'Notes': ''}}])
                for pubCode in pubRegex.findall(requestUrl):
                    returnResults.append([{'Phrase': pubCode,
                                           'Entity Type': 'Phrase'},
                                          {pageUid: {'Resolution': 'Google AdSense ca-pub Tracking Code',
                                                     'Notes': ''}}])
                for gtmCode in gtmRegex.findall(requestUrl):
                    returnResults.append([{'Phrase': gtmCode,
                                           'Entity Type': 'Phrase'},
                                          {pageUid: {'Resolution': 'Google GTM Tracking Code',
                                                     'Notes': ''}}])
                for gCode in gRegex.findall(requestUrl):
                    returnResults.append([{'Phrase': gCode,
                                           'Entity Type': 'Phrase'},
                                          {pageUid: {'Resolution': 'Google G Tracking Code',
                                                     'Notes': ''}}])
                for qCode in qualtricsRegex.findall(requestUrl):
                    returnResults.append([{'Phrase': qCode[6:],
                                           'Entity Type': 'Phrase'},
                                          {pageUid: {'Resolution': 'Qualtrics Tracking Code',
                                                     'Notes': ''}}])
                for pCode in pingdomRegex.findall(requestUrl):
                    returnResults.append([{'Phrase': pCode[:-3],
                                           'Entity Type': 'Phrase'},
                                          {pageUid: {'Resolution': 'Pingdom Tracking Code',
                                                     'Notes': ''}}])
                for mCode in mPulseRegex.findall(requestUrl):
                    returnResults.append([{'Phrase': mCode,
                                           'Entity Type': 'Phrase'},
                                          {pageUid: {'Resolution': 'mPulse Tracking Code',
                                                     'Notes': ''}}])
                for cCode in contextWebRegex.findall(requestUrl):
                    returnResults.append([{'Phrase': cCode.split('token=')[1].split('&')[0],
                                           'Entity Type': 'Phrase'},
                                          {pageUid: {'Resolution': 'ContextWeb Tracking Code',
                                                     'Notes': ''}}])
                for fCode in facebookRegex.findall(requestUrl):
                    returnResults.append([{'Phrase': fCode.split('id=')[1].split('&')[0],
                                           'Entity Type': 'Phrase'},
                                          {pageUid: {'Resolution': 'Facebook Tracking Pixel Code',
                                                     'Notes': ''}}])
                for mapsCode in googleMapsRegex.findall(requestUrl):
                    returnResults.append([{'Phrase': mapsCode.split('client=', 1)[1].split('&')[0],
                                           'Entity Type': 'Phrase'},
                                          {pageUid: {'Resolution': 'Google Maps Client Code',
                                                     'Notes': ''}}])
                for marketoCode in marketoRegex.findall(requestUrl):
                    returnResults.append([{'Phrase': marketoCode.split('aid=')[1].split('&')[0],
                                           'Entity Type': 'Phrase'},
                                          {pageUid: {'Resolution': 'Marketo Tracking Code',
                                                     'Notes': ''}}])
                for vwoCode in visualWebsiteOptimizerRegex.findall(requestUrl):
                    returnResults.append([{'Phrase': vwoCode.split('a=')[1].split('&')[0],
                                           'Entity Type': 'Phrase'},
                                          {pageUid: {'Resolution': 'Visual Website Optimizer Tracking User ID',
                                                     'Notes': ''}}])
                for oCode in optimizeRegex.findall(requestUrl):
                    returnResults.append([{'Phrase': oCode.split('id=')[1].split('&')[0],
                                           'Entity Type': 'Phrase'},
                                          {pageUid: {'Resolution': 'Google Optimize ID',
                                                     'Notes': ''}}])
                for mmCode in markMonitorRegex.findall(requestUrl):
                    returnResults.append([{'Phrase': mmCode.split('adv=')[1].split('&')[0],
                                           'Entity Type': 'Phrase'},
                                          {pageUid: {'Resolution': 'Mark Monitor Tracking ID',
                                                     'Notes': ''}}])
                for zCode in zendeskRegex.findall(requestUrl):
                    returnResults.append([{'Phrase': zCode.split('key=')[1].split('&')[0],
                                           'Entity Type': 'Phrase'},
                                          {pageUid: {'Resolution': 'Zendesk ID',
                                                     'Notes': ''}}])
                for qsCode in quantServeRegex.findall(requestUrl):
                    returnResults.append([{'Phrase': qsCode.split('/pixel/')[1].split('.gif')[0],
                                           'Entity Type': 'Phrase'},
                                          {pageUid: {'Resolution': 'QuantServe Tracking Pixel ID',
                                                     'Notes': ''}}])

        with sync_playwright() as p:
            browser = p.firefox.launch()
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0'
            )
            page = context.new_page()
            uid = None

            # Subscribe to "request" events.
            page.on("request", lambda request: GetTrackingCodes(uid, request.url))

            for site in entityJsonList:
                uid = site['uid']
                url = site.get('URL') if site.get('Entity Type', '') == 'Website' else site.get('Domain Name', None)
                if url is None:
                    continue
                if not url.startswith('http://') and not url.startswith('https://'):
                    url = 'http://' + url

                try:
                    page.goto(url)
                except Error:
                    pass
            page.close()
            browser.close()

        return returnResults
