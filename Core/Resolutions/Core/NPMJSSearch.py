#!/usr/bin/env python3


class NPMJSSearch:
    name = "Find NPM organization"
    category = "Online Identity"
    description = "Find a collective's npmjs organization page."
    originTypes = {'Phrase', 'Company', 'Organization'}
    resultTypes = {'Website'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import requests

        headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:108.0) Gecko/20100101 Firefox/108.0'}
        url_base = 'https://www.npmjs.com/org/'

        returnResults = []

        for entity in entityJsonList:
            primaryField = entity[list(entity)[1]].lower()

            string_checks = set()
            string_checks.add(''.join(primaryField.split(' ')))
            string_checks.add('_'.join(primaryField.split(' ')))
            string_checks.add('-'.join(primaryField.split(' ')))

            for check in string_checks:
                check_url = url_base + check
                request = requests.head(check_url, headers=headers)
                if request.status_code == 200:
                    returnResults.append([{'URL': check_url,
                                           'Entity Type': 'Website'},
                                          {entity['uid']: {'Resolution': 'NPMJS Org',
                                                           'Notes': ''}}])

        return returnResults
