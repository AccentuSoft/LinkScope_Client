#!/usr/bin/env python3

class GetExternalURLs:

    name = "Get External Urls"
    description = "Returns all links to external sites on a website."
    originTypes = {'Website'}
    resultTypes = {'Website'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        from selenium import webdriver
        from selenium.webdriver.firefox.options import Options as FirefoxOptions
        import urllib.parse
        links = []
        returnResult = []

        options = FirefoxOptions()
        options.headless = True
        driver = webdriver.Firefox(options=options)

        for site in entityJsonList:
            uid = site['uid']
            url = site['URL']
            if url is None:
                continue
            if not url.startswith('http://') and not url.startswith('https://'):
                url = 'http://' + url

            domain = ".".join(urllib.parse.urlparse(url).netloc.split('.')[-2:])
            driver.get(url)
            elements = driver.find_elements_by_tag_name("a")
            for element in elements:
                attr = element.get_attribute("href")
                if attr is None:
                    continue
                if domain not in attr:
                    if attr not in links:
                        links.append(attr)
            for link in links:
                returnResult.append([{'URL': link, 'Entity Type': 'Website'},
                                     {uid: {'Resolution': 'External Link', 'Notes': ''}}])
        if driver is not None:
            driver.quit()
        return returnResult
