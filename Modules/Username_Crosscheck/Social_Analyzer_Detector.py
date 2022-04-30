#!/usr/bin/env python3

"""
Note: Creates log files in temp folders in /tmp. Files are only readable by the person running the software.
"""


class Social_Analyzer_Detector:
    name = "Social Analyzer"
    category = "Online Identity"
    description = "Find potentially connected social media accounts."
    originTypes = {'Phrase', 'Social Media Handle'}
    resultTypes = {'Social Media Handle'}
    parameters = {'websites': {'description': 'Enter the domain names of the social media websites '
                                              'to check, separated with spaces, or "all" (no quotes) '
                                              'to check all available websites.\n'
                                              'E.g.: "github.com instagram.com" (no quotes).',
                               'type': 'String',
                               'default': 'all',
                               'value': 'Example input: facebook.com instagram.com'}}

    def resolution(self, entityJsonList, parameters):
        import requests
        from importlib import import_module
        from requests.exceptions import RequestException
        import random
        import string
        import re
        commentsRegex = re.compile('<!--.*?-->', re.DOTALL)
        websites = parameters['websites'].lower()

        headers = {
            'User-Agent': 'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:99.0) Gecko/20100101 Firefox/99.0',
        }

        def resolutionHelper(original_url):
            """
            Helper function that sends the web requests to each site. Due to the fact that some do not use https,
            certificate verification is disabled.
            """
            try:
                originalUsernameRegex = re.compile(re.escape(social_field), re.IGNORECASE)
                firstResponse = requests.get(original_url, verify=False, timeout=30, allow_redirects=False,  # nosec
                                             headers=headers)
                if firstResponse.status_code >= 300:
                    return False
                else:
                    modifiedUsername = "".join(random.choices(  # nosec
                        string.ascii_uppercase + string.digits, k=32))
                    usernameRegex = re.compile(social_field, re.IGNORECASE)
                    r = requests.get(original_url, timeout=30, verify=False, headers=headers)  # nosec
                    originalContent = r.text
                    if len(originalUsernameRegex.findall(originalContent)) == 0:
                        # False Positive
                        return False
                    modified_url = original_url.replace(social_field, modifiedUsername)
                    r = requests.get(modified_url, timeout=30, verify=False, headers=headers)  # nosec
                    modifiedUsernameContent = r.text
                    for regexMatch in commentsRegex.findall(originalContent):
                        originalContent = originalContent.replace(regexMatch, '')
                    for regexMatch in commentsRegex.findall(modifiedUsernameContent):
                        modifiedUsernameContent = modifiedUsernameContent.replace(regexMatch, '')
                    for regexMatch in usernameRegex.findall(originalContent):
                        originalContent = originalContent.replace(regexMatch, modifiedUsername)
                    if modifiedUsernameContent == originalContent:
                        # False positive
                        return False
                    else:
                        return [{'URL': original_url,
                                 'Entity Type': 'Website'},
                                {uid: {'Resolution': 'Social Analyzer Report', 'Notes': ''}}]
            except (ConnectionError, RequestException) as error:
                return "Connection error: " + str(error)

        return_result = []
        for entity in entityJsonList:
            # Have to keep re-importing so that it works for entities beyond the first.
            SocialAnalyzer = import_module("social-analyzer").SocialAnalyzer(silent=True)
            uid = entity['uid']
            if entity['Entity Type'] == 'Phrase':
                social_field = entity['Phrase']
            elif entity['Entity Type'] == 'Social Media Handle':
                social_field = entity['User Name']
            else:
                continue
            social_field = social_field.strip().lower()
            results = SocialAnalyzer.run_as_object(
                username=social_field, silent=True, output="json", filter='good', metadata=False, logs_dir='',
                websites=websites, mode='fast', timeout=15, profiles='detected')

            # Social Analyzer can return false positives. Verifying the results cuts down on those.
            # In some *very* rare cases this might result in false negatives, but we have not been able to find any
            #   examples of this.
            if len(results) != 0:
                for link in results['detected']:
                    url = link['link']
                    helperResult = resolutionHelper(url)
                    if isinstance(helperResult, list):
                        return_result.append(helperResult)
        return return_result
