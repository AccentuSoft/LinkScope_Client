#!/usr/bin/env python3


class ReverseWhois:

    name = "Discover Domains Owned by Entity"

    category = "Reverse Whois"

    description = "Discover Domains Owned by Entity through reverse whois lookup"

    originTypes = {'Phrase', 'Company', 'Person'}

    resultTypes = {'Domain, Company'}

    parameters = {'Max Results': {'description': 'Please enter the maximum number of domains to return.',
                                  'type': 'String',
                                  'value': 'Maximum number of results',
                                  'default': '0'},
                  }

    def resolution(self, entityJsonList, parameters):
        import requests
        import bs4
        import re
        returnResults = []
        domains = []
        registrars = []

        try:
            linkNumbers = int(parameters['Max Results'])
        except ValueError:
            return "Non-integer input provided for 'Max Results' parameter. Cannot execute resolution."
        if linkNumbers <= 0:
            return []

        for entity in entityJsonList:
            uid = entity['uid']
            qry = entity[list(entity)[1]]
            url = f"https://reversewhois.io?searchterm={qry}"

            try:
                res = requests.get(url)
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"

            if res.status_code > 200:
                continue

            html = bs4.BeautifulSoup(res.content, features="lxml")
            date_regex = re.compile(r'\d{4}-\d{2}-\d{2}')

            for table_row in html.findAll("tr"):
                table_cells = table_row.findAll("td")
                # make double-sure we're in the right table by checking the date field
                try:
                    if date_regex.match(table_cells[2].text.strip()):
                        domain = table_cells[1].text.strip().lower()
                        registrar = table_cells[-1].text.strip()
                        if domain:
                            domains.append(domain)
                        if registrar:
                            registrars.append(registrar)

                except IndexError:
                    continue

            if linkNumbers >= len(domains):
                linkNumbers = int(len(domains))

            for j in range(max(len(domains), len(registrars))):
                index_of_child = len(returnResults)
                if j < len(domains):
                    returnResults.append([{'Domain Name': domains[j],
                                           'Entity Type': 'Domain'},
                                          {uid: {'Resolution': 'Domain',
                                                 'Notes': ''}}])
                if j < len(registrars):
                    returnResults.append([{'Company Name': registrars[j],
                                           'Entity Type': 'Company'},
                                          {index_of_child: {'Resolution': 'Registrar',
                                                            'Notes': ''}}])
        return returnResults
