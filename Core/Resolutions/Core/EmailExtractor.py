#!/usr/bin/env python3


class EmailExtractor:
    # A string that is treated as the name of this resolution.
    name = "Extract Emails"

    category = "Website Information"

    # A string that describes this resolution.
    description = "Returns the email addresses present on a website or index page of a domain."

    originTypes = {'Domain', 'Website'}

    resultTypes = {'Email Address'}

    parameters = {'Max Depth': {'description': 'Each link leading to another website in the same domain can be '
                                               'explored to discover more entities. Each entity discovered after '
                                               'exploring sites linked in the original website or domain is said to '
                                               'have a "depth" value of 1. Entities found from exploring the links on '
                                               'this page would have a "depth" of 2, and so on. A larger value could '
                                               'result in EXPONENTIALLY more time taken to finish the resolution.\n'
                                               'The default value is "0", which means only the provided website, or '
                                               'the index page of the domain provided, is explored.',
                                'type': 'String',
                                'value': '0',
                                'default': '0'},
                  'Use Regex': {'description': 'Extraction of emails is done by finding "mailto" links in the source '
                                               'code of the website. However, not all emails on the site may exist in '
                                               'that format. Using Regex can result in more emails being extracted, '
                                               'however it is possible that some false positives may be extracted '
                                               'too.\nDo you want to also use Regex to extract emails, in addition to '
                                               'the default extraction method?',
                                'type': 'SingleChoice',
                                'value': {'Yes', 'No'},
                                'default': 'Yes'},
                  'Verify Email Domain Validity': {'description': 'Verification checks are performed on extracted '
                                                                  'emails to ensure that they are valid and working '
                                                                  'email addresses. One of these checks involves '
                                                                  'attempting to resolve the email address domain. '
                                                                  'This will generate network traffic.\n'
                                                                  'Do you want to verify email domain validity?',
                                                   'type': 'SingleChoice',
                                                   'value': {'Yes', 'No'},
                                                   'default': 'No'}
                  }

    def resolution(self, entityJsonList, parameters):
        from playwright.sync_api import sync_playwright, TimeoutError, Error
        from bs4 import BeautifulSoup
        import tldextract
        import re
        from email_validator import validate_email, caching_resolver, EmailNotValidError

        returnResults = []

        # Numbers less than zero are the same as zero, but we should try to prevent overflows.
        try:
            maxDepth = max(int(parameters['Max Depth']), 0)
        except ValueError:
            return "Invalid value provided for Max Webpages to follow."

        # Source: https://emailregex.com/
        # Alt: (?:[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(\.([a-zA-Z0-9-])+)+)
        emailRegex = re.compile(r"""(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])""")
        useRegex = True if parameters['Use Regex'] == 'Yes' else False

        resolver = caching_resolver(timeout=10)
        verifyDomain = True if parameters['Verify Email Domain Validity'] == 'Yes' else False

        exploredDepth = set()

        # The software can deduplicate, but handling it here is better.
        allEmails = set()

        def extractEmails(currentUID: str, site: str, depth: int):
            page = context.new_page()
            pageResolved = False
            for _ in range(3):
                try:
                    page.goto(site, wait_until="networkidle", timeout=10000)
                    pageResolved = True
                    break
                except TimeoutError:
                    pass
                except Error:
                    break
            if not pageResolved:
                # Last chance for this to work; some pages have issues with the "networkidle" trigger.
                try:
                    page.goto(site, wait_until="load", timeout=10000)
                except Error:
                    return

            soupContents = BeautifulSoup(page.content(), 'lxml')
            if useRegex:
                # Remove <span> and <noscript> tags, and attempt some basic de-obfuscation.
                while True:
                    try:
                        soupContents.noscript.extract()
                    except AttributeError:
                        break
                while True:
                    try:
                        soupContents.span.extract()
                    except AttributeError:
                        break
                siteContent = soupContents.get_text()
                siteContent = re.sub(r'\s*(\[|\<|\()+\s*at\s*(\]|\>|\))+\s*', '@', siteContent)
                siteContent = re.sub(r'\s*(\[|\<|\()+\s*dot\s*(\]|\>|\))+\s*', '.', siteContent)
                siteContent = re.sub(r'\s*(\[|\<|\()+\s*\.\s*(\]|\>|\))+\s*', '.', siteContent)

                potentialEmails = emailRegex.findall(siteContent)
                for potentialEmail in potentialEmails:
                    try:
                        valid = validate_email(potentialEmail, dns_resolver=resolver, check_deliverability=verifyDomain)
                        if valid.email not in allEmails:
                            allEmails.add(valid.email)
                            returnResults.append([{'Email Address': valid.email,
                                                   'Entity Type': 'Email Address'},
                                                  {currentUID: {'Resolution': 'Email Address Found',
                                                                'Notes': ''}}])
                    except EmailNotValidError:
                        pass
            linksInAHref = soupContents.find_all('a')
            for tag in linksInAHref:
                newLink = tag.get('href', None)
                if newLink is not None:
                    if newLink.startswith('mailto:'):
                        try:
                            valid = validate_email(newLink[7:], dns_resolver=resolver,
                                                   check_deliverability=verifyDomain)
                            if valid.email not in allEmails:
                                allEmails.add(valid.email)
                                returnResults.append([{'Email Address': valid.email,
                                                       'Entity Type': 'Email Address'},
                                                      {currentUID: {'Resolution': 'Email Address Found',
                                                                    'Notes': ''}}])
                        except EmailNotValidError:
                            pass
                    elif newLink.startswith('http'):
                        newLink = newLink.split('#')[0]
                        newDepth = depth - 1
                        if domain in newLink and newLink not in exploredDepth and newDepth > 0:
                            exploredDepth.add(newLink)
                            extractEmails(currentUID, newLink, newDepth)

            linksInLinkHref = soupContents.find_all('link')
            for tag in linksInLinkHref:
                newLink = tag.get('href', None)
                if newLink is not None:
                    if newLink.startswith('http'):
                        newLink = newLink.split('#')[0]
                        newDepth = depth - 1
                        if domain in newLink and newLink not in exploredDepth and newDepth > 0:
                            exploredDepth.add(newLink)
                            extractEmails(currentUID, newLink, newDepth)

        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/101.0.4951.54 Safari/537.36'
            )
            for entity in entityJsonList:
                uid = entity['uid']
                url = entity.get('URL') if entity.get('Entity Type', '') == 'Website' else \
                    entity.get('Domain Name', None)
                if url is None:
                    continue
                if not url.startswith('http://') and not url.startswith('https://'):
                    url = 'http://' + url
                domain = tldextract.extract(url).fqdn
                extractEmails(uid, url, maxDepth)
            browser.close()

        return returnResults
