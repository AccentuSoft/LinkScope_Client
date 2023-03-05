#!/usr/bin/env python3


class DoTheyExist:
    name = "JS-Based Account Check"
    category = "Online Identity"
    description = "Check if an email, username or phone number exists as part of an account in certain sites. " \
                  "The checks involve sites that do not explicitly respond to enumeration attempts in a way that can " \
                  "be detected without Javascript."
    originTypes = {'Email Address', 'Phone Number', 'Phrase'}
    resultTypes = {'Domain'}

    parameters = {'Include Noisy Checks': {'description': 'Should we check for accounts in domains that will notify '
                                                          'the user that someone is investigating them?',
                                           'type': 'SingleChoice',
                                           'value': {'Include noisy sites', 'Do not include noisy sites'},
                                           'default': 'Do not include noisy sites'}}

    def resolution(self, entityJsonList, parameters):
        import json
        import tldextract
        from pathlib import Path
        from playwright.sync_api import sync_playwright, Error
        from time import sleep

        directory = Path(__file__).parent.resolve()
        with open(directory / 'js_web_accounts_json.json') as web_accounts_list:
            file = json.load(web_accounts_list)
        noisyParameter = parameters['Include Noisy Checks'] == 'Do not include noisy sites'

        returnResults = []

        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()

            for entity in entityJsonList:
                uid = entity['uid']
                entityType = entity['Entity Type']
                primaryField = entity[list(entity)[1]]

                for site in file['sites']:
                    if not site['enabled']:
                        continue
                    if (entityType == 'Email Address' and not site['accepts_email']) or \
                            (entityType == 'Phrase' and not site['accepts_username']) or \
                            (entityType == 'Phone Number' and not site['accepts_phone']):
                        continue
                    if site['noisy'] and noisyParameter:
                        continue
                    try:
                        siteURL = site['login_page']
                        page.goto(siteURL)
                        sleep(1)

                        for preparationLocator in site['preparation_locators']:
                            if preparationLocator[1]:
                                page.frame_locator(preparationLocator[1]).locator(preparationLocator[0]).click()
                            else:
                                page.locator(preparationLocator[0]).click()

                        page.locator(site['login_username_locator']).fill(primaryField)

                        if usernameSubmitLocator := site[
                            'username_submit_locator'
                        ]:
                            page.locator(usernameSubmitLocator).click()

                        if passwordLocator := site['password_locator']:
                            page.locator(passwordLocator).fill('aaaaaa')
                        page.locator(site['login_submit_locator']).click()

                        try:
                            page.locator(site['account_missing_locator']).focus(timeout=10000)
                            # If we hit the missing locator, then move on to the next site to check.
                            continue
                        except Error:
                            # If we can't find the missing locator, continue as normal.
                            pass

                        for successLocator in site['account_existence_locators']:
                            try:
                                # We've already waited 10 secs for the missing locator, we can speed through finding
                                #   the success locator.
                                page.locator(successLocator).focus(timeout=500)
                                returnResults.append([{'Domain Name': tldextract.extract(siteURL).fqdn,
                                                       'Entity Type': 'Domain'},
                                                      {uid: {'Resolution': 'Account Found',
                                                             'Notes': ''}}])
                                break
                            except Error:
                                pass
                    except Error:
                        continue

                sleep(5)

        return returnResults
