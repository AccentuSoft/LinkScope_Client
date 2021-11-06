#!/usr/bin/env python3


class BigMatch:
    name = "BigMatch Search"
    description = "Find information about a file using https://bigmatch.rev.ng/static/index.html"
    originTypes = {"Image", "Document", "Archive"}
    resultTypes = {'Website'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        from pathlib import Path
        from selenium import webdriver
        from selenium.common.exceptions import SessionNotCreatedException
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from bs4 import BeautifulSoup, SoupStrainer

        return_result = []

        url = "https://bigmatch.rev.ng/static/index.html"
        try:
            fireFoxOptions = webdriver.FirefoxOptions()
            fireFoxOptions.headless = True
            driver = webdriver.Firefox(options=fireFoxOptions)
        except SessionNotCreatedException:
            return "Please install the latest version of Firefox from the official Firefox website"
        for entity in entityJsonList:
            uid = entity['uid']
            file_path = Path(entity["File Path"])
            if not (file_path.exists() and file_path.is_file()):
                continue
            driver.implicitly_wait(3)
            driver.get(url)
            element = driver.find_element(By.ID, "input")
            element.send_keys(str(file_path))  # Windows Compatibility
            wait = WebDriverWait(driver, 5)
            wait.until(EC.element_to_be_clickable((By.ID, 'results')))
            response = driver.page_source
            for link in BeautifulSoup(response, 'html.parser', parse_only=SoupStrainer('a')):
                if link.has_attr('href'):
                    if "github" in link['href']:
                        return_result.append([{'URL': link['href'], 'Entity Type': 'Website'},
                                             {uid: {'Resolution': 'BigMatch Github Link', 'Notes': ''}}])

        return return_result
