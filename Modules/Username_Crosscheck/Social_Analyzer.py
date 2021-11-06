#!/usr/bin/env python3


class Social_Analyzer:
    name = "Social Analyzer"
    description = "Find information about a persons social media accounts"
    originTypes = {'Phrase'}
    resultTypes = {'Social Media Account'}
    parameters = {'websites': {'description': 'Enter the domain names of the social media websites'
                               ' to check or "all" (no quotes) to check all available websites.'
                               ' Note that some of the results could be false positives.',
                               'type': 'String',
                               'default': 'all',
                               'value': 'e.g: Facebook.com, Instagram.com etc...'}}

    def resolution(self, entityJsonList, parameters):
        import requests
        from importlib import import_module
        from requests.exceptions import RequestException
        import time
        import random
        import string
        import re
        commentsRegex = re.compile('<!--.*?-->', re.DOTALL)
        websites = parameters['websites']

        def resolutionHelper(uid, social_field, original_url):
            """
            Helper function that sends the web requests to each site. Due to the fact that some do not use https,
            certificate verification is disabled.

            :param uid:
            :param social_field:
            :param original_url:
            :return:
            """
            try:
                originalUsernameRegex = re.escape(social_field)
                originalUsernameRegex2 = re.compile(originalUsernameRegex, re.IGNORECASE)
                firstResponse = requests.get(original_url, verify=False, timeout=30, allow_redirects=False)  # nosec
                if firstResponse.status_code >= 300:
                    return False
                else:
                    modifiedUsername = "".join(random.choices(
                        string.ascii_uppercase + string.digits, k=32))
                    usernameRegex = re.compile(social_field, re.IGNORECASE)
                    r = requests.get(original_url, timeout=30, verify=False)  # nosec
                    originalContent = r.text
                    if len(originalUsernameRegex2.findall(originalContent)) == 0:
                        print(f"false positive (no {social_field} found in the content of:")
                        print(original_url)
                        return False
                    modified_url = original_url.replace(social_field, modifiedUsername)
                    r = requests.get(modified_url, timeout=30, verify=False)  # nosec
                    modifiedUsernameContent = r.text
                    for regexMatch in commentsRegex.findall(originalContent):
                        originalContent = originalContent.replace(regexMatch, '')
                    for regexMatch in commentsRegex.findall(modifiedUsernameContent):
                        modifiedUsernameContent = modifiedUsernameContent.replace(regexMatch, '')
                    for regexMatch in usernameRegex.findall(originalContent):
                        originalContent = originalContent.replace(regexMatch, modifiedUsername)
                    if modifiedUsernameContent == originalContent:
                        print("false positive:", original_url)
                        return False
                    else:
                        return [{'Profile Link': original_url,
                                 'Entity Type': 'Social Media Account'},
                                {uid: {'Resolution': 'Social Analyzer Report', 'Notes': ''}}]
            except (ConnectionError, RequestException) as error:
                return "Connection error: " + str(error)
        SocialAnalyzer = import_module("social-analyzer").SocialAnalyzer(silent=True)

        return_result = []
        for entity in entityJsonList:
            uid = entity['uid']
            social_field = entity[list(entity)[1]].strip()
            results = SocialAnalyzer.run_as_object(
                username=str(social_field), silent=True, output="json", filter='good', metadata=False, logs_dir='',
                websites=websites, mode='fast', timeout=10, profiles='detected')
            if len(results) != 0:
                for link in results['detected']:
                    url = link['link']
                    count = 0
                    helperResult = resolutionHelper(uid, social_field, url)
                    while helperResult is None:
                        time.sleep(5)
                        count += 1
                        if count == 3:
                            break
                        helperResult = resolutionHelper(uid, social_field, url)
                    if count != 3 and helperResult is not False:
                        return_result.append(helperResult)
        return return_result
