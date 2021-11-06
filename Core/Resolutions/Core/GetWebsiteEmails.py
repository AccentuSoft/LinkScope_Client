#!/usr/bin/env python3


class GetWebsiteEmails:
    # A string that is treated as the name of this resolution.
    name = "Get Emails In Website"

    # A string that describes this resolution.
    description = "Returns Nodes of emails for websites"

    originTypes = {'Website'}

    resultTypes = {'Phrase'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import requests
        import re
        from email_validator import validate_email, caching_resolver, EmailNotValidError

        headers = {
            'User-Agent': 'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        }

        returnResults = []
        emails = set()

        for entity in entityJsonList:
            uid = entity['uid']

            primaryField = entity[list(entity)[1]]

            if primaryField.startswith('http://') or primaryField.startswith('https://'):
                url = primaryField
            else:
                url = 'http://' + primaryField

            r = requests.get(url, headers=headers)
            doc = r.text

            new_emails = set(re.findall(r"[\w.-]+@[\w.-]+", doc, re.IGNORECASE))
            emails.update(new_emails)

            resolver = caching_resolver(timeout=10)
            for mail in emails:
                try:
                    # Validate.
                    valid = validate_email(mail, dns_resolver=resolver)

                    returnResults.append([{'Email Address': valid.email,
                                           'Entity Type': 'Email Address'},
                                          {uid: {'Resolution': 'Email Found', 'Name': 'Emails Found', 'Notes': ''}}])
                except EmailNotValidError as e:
                    # email is not valid, exception message is human-readable
                    returnResults.append([{'Phrase': str(e),
                                           'Entity Type': 'Phrase'},
                                          {uid: {'Resolution': 'Email Found', 'Name': 'Emails Found', 'Notes': ''}}])
        return returnResults
