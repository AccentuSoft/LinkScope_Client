#!/usr/bin/env python3

class GetDForms:
    # A string that is treated as the name of this resolution.
    name = "Get Recent D Forms"

    category = "EDGAR Info"

    # A string that describes this resolution.
    description = "Returns Nodes D Forms"

    originTypes = {'Edgar ID'}

    resultTypes = {'FormD, Person, Address, Phrase'}

    parameters = {'Max Results': {'description': 'Please enter the maximum number of results to return.\n'
                                                 'Returns the 5 most recent by default.',
                                  'type': 'String',
                                  'default': '5'}}

    def resolution(self, entityJsonList, parameters):
        import requests
        import time
        import xmltodict
        import json
        from bs4 import BeautifulSoup
        from ast import literal_eval

        headers = {
            'User-Agent': 'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        }

        try:
            linkNumbers = int(parameters['Max Results'])
        except ValueError:
            return "Invalid integer provided in 'Max Results' parameter"
        if linkNumbers <= 0:
            return []
        returnResults = []
        for entity in entityJsonList:
            archives_set = set()
            uid = entity['uid']
            cik = entity['CIK']
            if cik.lower().startswith('cik'):
                cik = cik.split('cik')[1]
            if len(cik) != 10:
                cik = cik.zfill(10)
            search_url = f'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&owner=include&count' \
                         f'={linkNumbers}&type=D'
            time.sleep(1)
            r = requests.get(search_url, headers=headers)
            if r.status_code != 200:
                return []

            soup = BeautifulSoup(r.text, "lxml")

            for link in soup.find_all('a'):
                # extract link url from the anchor
                anchor = link.attrs['href'] if 'href' in link.attrs else ''
                if '/Archives/edgar/data/' in anchor:
                    anchor = 'https://www.sec.gov' + anchor
                    archives_set.add(anchor)

            for archive in archives_set:
                time.sleep(1)
                r = requests.get(archive, headers=headers)
                soup = BeautifulSoup(r.text, "lxml")
                for link in soup.find_all('a'):
                    # extract link url from the anchor
                    anchor = link.attrs['href'] if 'href' in link.attrs else ''
                    if '/Archives/edgar/data/' in anchor and 'primary_doc.xml' in anchor \
                            and 'xslFormDX01' not in anchor:
                        time.sleep(1)
                        anchor = 'https://www.sec.gov' + anchor
                        r = requests.get(anchor, headers=headers)
                        data = (json.dumps(xmltodict.parse(r.text))).replace('null', 'None')
                        data = literal_eval(data)
                        # print(data)

                        value = data['edgarSubmission']['offeringData']
                        index_of_child = len(returnResults)
                        returnResults.append([{'Company Name': 'D: ' + data['edgarSubmission']['primaryIssuer']
                        ['entityName'] + ' ' + value['signatureBlock']['signature']['signatureDate'],
                                               'Industry Group Type': value['industryGroup']['industryGroupType'],
                                               'Investment Fund Type': value['industryGroup']['investmentFundInfo']
                                               ['investmentFundType'],
                                               'Aggregate Net Asset Value Range': value['issuerSize']
                                               ['aggregateNetAssetValueRange'],
                                               'Duration Of Offering': 'More Than one Year: ' +
                                                                       value['durationOfOffering']['moreThanOneYear'],
                                               'Types Of Securities Offered': 'Pooled Investment Fund Type: ' +
                                                                              value['typesOfSecuritiesOffered'][
                                                                                  'isPooledInvestmentFundType'],
                                               'Business Combination Transaction': 'Business Combination Transaction: '
                                                                                   + value[
                                                                                       'businessCombinationTransaction'][
                                                                                       'isBusinessCombinationTransaction'],
                                               'Minimum Investment Accepted': value['minimumInvestmentAccepted'],
                                               'Total Offering Amount': value['offeringSalesAmounts']
                                               ['totalOfferingAmount'],
                                               'Total Amount Sold': value['offeringSalesAmounts']['totalAmountSold'],
                                               'Total Amount Remaining': value['offeringSalesAmounts'][
                                                   'totalRemaining'],
                                               'Has Non Accredited Investors': 'Non Accredited Investors'
                                                                               + value['investors'][
                                                                                   'hasNonAccreditedInvestors'],
                                               'Total Number Already Invested': value['investors']
                                               ['totalNumberAlreadyInvested'],
                                               'Sales Commissions': value['salesCommissionsFindersFees']
                                               ['salesCommissions']['dollarAmount'],
                                               'Finders Fees': value['salesCommissionsFindersFees']['findersFees']
                                               ['dollarAmount'],
                                               'Gross Proceeds Used': value['useOfProceeds']['grossProceedsUsed']
                                               ['dollarAmount'],
                                               'Notes': '',

                                               'Entity Type': 'FormD'},
                                              {uid: {'Resolution': 'D Form',
                                                     'Notes': ''}}])

                        people = data['edgarSubmission']['relatedPersonsList']['relatedPersonInfo']
                        for person in people:
                            child_of_child = len(returnResults)
                            returnResults.append([{'Full Name': person['relatedPersonName']['firstName'] + ' ' +
                                                                person['relatedPersonName']['lastName'],
                                                   'Entity Type': 'Person'},
                                                  {index_of_child: {'Resolution': 'Officer',
                                                                    'Notes': ''}}])

                            returnResults.append(
                                [{'Street Address': person['relatedPersonAddress']['street1'],
                                  'Locality': person['relatedPersonAddress']['city'],
                                  'Postal Code': person['relatedPersonAddress']['zipCode'],
                                  'Country': person['relatedPersonAddress']['stateOrCountryDescription'],
                                  'Entity Type': 'Address'},
                                 {child_of_child: {'Resolution': 'Location', 'Notes': ''}}])

                            returnResults.append(
                                [{'Phrase': person['relatedPersonRelationshipList']['relationship'],
                                  'Entity Type': 'Phrase'},
                                 {child_of_child: {'Resolution': 'Relationship', 'Notes': ''}}])

                            if person['relationshipClarification'] is not None:
                                returnResults.append(
                                    [{'Phrase': person['relationshipClarification'],
                                      'Entity Type': 'Phrase'},
                                     {child_of_child: {'Resolution': 'Relationship', 'Notes': ''}}])

        return returnResults
