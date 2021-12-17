#!/usr/bin/env python3


class Whats_My_Name:
    """
    The file web_accounts_list.json is required for the resolution Whats_My_Name.
    Find:true
    Replace:true,\n        "requires_javascript" : false
    Find: "valid" : true
    Replace: "valid" : "True"
    Find: "valid" : false
    Replace: "valid" : "False"
    """

    name = "Whats My Name"
    description = "Find information about a persons social media accounts"
    originTypes = {'Phrase', 'Person'}
    resultTypes = {'Website'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        from requests_futures.sessions import FuturesSession
        from concurrent.futures import as_completed
        from pathlib import Path
        import json
        from playwright.sync_api import sync_playwright, TimeoutError

        import re
        from requests.exceptions import RequestException
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:94.0) Gecko/20100101 Firefox/94.0',
        }

        futures = {}
        return_result = []

        with sync_playwright() as p:
            browser = p.firefox.launch()
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0'
            )
            page = context.new_page()

            for entity in entityJsonList:
                uid = entity['uid']
                # Most services do not care about capitalization.
                # Some may redirect non-lowercase usernames, which could result in missed accounts.
                social_field = entity[list(entity)[1]].strip().lower()
                directory = Path(__file__).parent.resolve()
                file_location = directory / 'web_accounts_list.json'
                file = open(file_location, 'r').read()
                file = json.loads(file)

                with FuturesSession(max_workers=15) as session:
                    for site in file['sites']:
                        original_uri = site['check_uri'].replace('{account}', social_field)
                        account_existence_code = str(site['account_existence_code'])
                        account_existence_string = site['account_existence_string']
                        requires_javascript = site['requires_javascript']
                        if site['valid'] == "True":
                            account_existence_string = re.escape(str(account_existence_string))
                            account_existence_string = re.compile(account_existence_string)
                            if requires_javascript == "True":
                                for _ in range(3):
                                    try:
                                        response = page.goto(original_uri, wait_until="networkidle", timeout=10000)
                                        status_code = response.status
                                        page_source = page.content()
                                        if status_code == int(account_existence_code) and \
                                            account_existence_string != "" and \
                                                len(account_existence_string.findall(page_source)) > 0:
                                            return_result.append([{'URL': original_uri,
                                                                   'Entity Type': 'Website'},
                                                                  {uid: {'Resolution': 'Whats My Name Account Match',
                                                                         'Notes': ''}}])
                                        break
                                    except TimeoutError:
                                        pass

                            else:
                                futures[session.get(original_uri, headers=headers,
                                                    timeout=10, allow_redirects=False)] = \
                                    (account_existence_code, account_existence_string)
                for future in as_completed(futures):
                    account_existence_code = futures[future][0]
                    account_existence_string = futures[future][1]
                    try:
                        first_response = future.result()
                    except RequestException:
                        continue
                    page_source = first_response.text
                    if first_response.status_code == int(account_existence_code) and \
                            account_existence_string != "" and \
                            len(account_existence_string.findall(page_source)) > 0:
                        return_result.append([{'URL': first_response.url,
                                               'Entity Type': 'Website'},
                                              {uid: {'Resolution': 'Whats My Name Account Match', 'Notes': ''}}])
            page.close()
            browser.close()
        return return_result
