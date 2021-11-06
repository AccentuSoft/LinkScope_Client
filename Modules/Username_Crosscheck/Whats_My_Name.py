#!/usr/bin/env python3


class Whats_My_Name:
    """
    The file web_accounts_list.json is required for the resolution Whats_My_Name.
    Find:true
    Replace:true,\n        "selenium" : false
    Find: true
    Replace: "True"
    Find: false
    Replace: "False"
    """

    name = "Whats My Name"
    description = "Find information about a persons social media accounts"
    originTypes = {'Phrase', 'Person'}
    resultTypes = {'Social Media Account'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        from requests_futures.sessions import FuturesSession
        from concurrent.futures import as_completed
        from pathlib import Path
        import json
        from seleniumwire import webdriver
        from selenium.common.exceptions import SessionNotCreatedException
        from selenium.common.exceptions import WebDriverException
        import re
        from requests.exceptions import RequestException
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:92.0) Gecko/20100101 Firefox/92.0',
        }

        futures = []
        site_params = []
        return_result = []

        try:
            fireFoxOptions = webdriver.FirefoxOptions()
            fireFoxOptions.headless = True
            driver = webdriver.Firefox(options=fireFoxOptions)
        except SessionNotCreatedException:
            return "Please install the latest version of Firefox from the official Firefox website"
        except WebDriverException:
            return "Please add geckodriver to your path."
        for entity in entityJsonList:
            uid = entity['uid']
            social_field = entity[list(entity)[1]].strip()
            directory = Path(__file__).parent.resolve()
            file_location = directory / 'web_accounts_list.json'
            file = open(file_location, 'r').read()
            file = json.loads(file)

            with FuturesSession(max_workers=15) as session:
                for site in file['sites']:
                    original_uri = site['check_uri'].replace('{account}', social_field)
                    account_existence_code = str(site['account_existence_code'])
                    account_existence_string = site['account_existence_string']
                    use_selenium = site['selenium']
                    if site['valid'] == "True":
                        if use_selenium == "True":
                            account_existence_string = re.escape(str(account_existence_string))
                            account_existence_string = re.compile(account_existence_string)
                            driver.get(original_uri)
                            status_code = driver.requests[0].response.status_code
                            page_source = driver.page_source
                            if status_code == int(
                                    account_existence_code) and account_existence_string != "" and len(
                                    account_existence_string.findall(page_source)) > 0:
                                return_result.append([{'URL': original_uri,
                                                       'Entity Type': 'Website'},
                                                      {uid: {'Resolution': 'Whats My Name Report', 'Notes': ''}}])
                        else:
                            futures.append(session.get(original_uri,
                                                       headers=headers, timeout=10, allow_redirects=False))
                            site_params.append((account_existence_code, account_existence_string))
            for future in as_completed(futures):
                account_existence_code = site_params[futures.index(future)][0]
                account_existence_string = site_params[futures.index(future)][1]
                account_existence_string = re.escape(str(account_existence_string))
                account_existence_string = re.compile(account_existence_string)
                try:
                    first_response = future.result()
                except RequestException:
                    continue
                page_source = first_response.text
                if first_response.status_code == int(account_existence_code) and account_existence_string != "" and len(
                        account_existence_string.findall(page_source)) > 0:
                    return_result.append([{'URL': first_response.url,
                                           'Entity Type': 'Website'},
                                          {uid: {'Resolution': 'Whats My Name Report', 'Notes': ''}}])
        return return_result
