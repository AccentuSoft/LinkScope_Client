#!/usr/bin/env python3

class GetNMFP2Forms:
    # A string that is treated as the name of this resolution.
    name = "Get Recent N-MFP2 Forms"

    # A string that describes this resolution.
    description = "Returns Nodes N-MFP2 Forms"

    originTypes = {'Edgar ID'}

    resultTypes = {'Collateral Issuer, Company, Phrase, FormNMFP2, CUSIP, LEIID, ISINID'}

    parameters = {'Max Results': {'description': 'Please enter the maximum number of results to return.\n'
                                                 'Returns the 5 most recent by default.',
                                  'type': 'String',
                                  'default': '5'}}

    def resolution(self, entityJsonList, parameters):
        import requests
        import xmltodict
        import json
        from playwright.sync_api import sync_playwright, TimeoutError
        from bs4 import BeautifulSoup
        from ast import literal_eval

        headers = {
            'User-Agent': 'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0',
        }

        try:
            maxResults = int(parameters['Max Results'])
        except ValueError:
            return "Invalid integer value provided for 'Max Results' parameter."
        if maxResults <= 0:
            return []

        returnResults = []
        liquidAssets = ['totalValueDailyLiquidAssets', 'totalValueWeeklyLiquidAssets', 'percentageDailyLiquidAssets',
                        'percentageWeeklyLiquidAssets', 'netAssetValue']
        seriesLevelInfoKeys = ['feederFundFlag', 'masterFundFlag', 'seriesFundInsuCmpnySepAccntFlag',
                               'fundExemptRetailFlag', 'averagePortfolioMaturity',
                               'averageLifeMaturity', 'cash',
                               'totalValuePortfolioSecurities', 'amortizedCostPortfolioSecurities',
                               'totalValueOtherAssets', 'totalValueLiabilities', 'netAssetOfSeries',
                               'numberOfSharesOutstanding', 'stablePricePerShare', 'sevenDayGrossYield']
        classLevelInfoKeys = ['minInitialInvestment', 'netAssetsOfClass', 'numberOfSharesOutstanding',
                              'sevenDayNetYield', 'personPayForFundFlag']
        securitiesInfoKeys = ['titleOfIssuer', 'investmentCategory', 'securityEligibilityFlag',
                              'investmentMaturityDateWAM', 'investmentMaturityDateWAL',
                              'finalLegalInvestmentMaturityDate', 'securityDemandFeatureFlag', 'securityGuaranteeFlag',
                              'securityEnhancementsFlag', 'yieldOfTheSecurityAsOfReportingDate',
                              'includingValueOfAnySponsorSupport', 'excludingValueOfAnySponsorSupport',
                              'percentageOfMoneyMarketFundNetAssets', 'securityCategorizedAtLevel3Flag',
                              'dailyLiquidAssetSecurityFlag', 'weeklyLiquidAssetSecurityFlag', 'illiquidSecurityFlag']

        with sync_playwright() as p:
            browser = p.firefox.launch()
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0'
            )
            page = context.new_page()
            for entity in entityJsonList:
                archives_set = set()
                uid = entity['uid']
                cik = entity['CIK']
                if cik.lower().startswith('cik'):
                    cik = cik.split('cik')[1]
                if len(cik) != 10:
                    cik = cik.zfill(10)
                search_url = f'https://www.sec.gov/edgar/search/#/category=custom&entityName={cik}&forms=N-MFP2'
                page.wait_for_timeout(1000)
                pageResolved = False
                for _ in range(3):
                    try:
                        page.goto(search_url, wait_until="networkidle", timeout=10000)
                        pageResolved = True
                        break
                    except TimeoutError:
                        pass
                if not pageResolved:
                    continue
                page.wait_for_timeout(1000)

                soup = BeautifulSoup(page.content(), "lxml")

                for link in soup.find_all('a'):
                    # extract link url from the anchor
                    anchor = link.attrs['data-adsh'] if 'data-adsh' in link.attrs else ''
                    if anchor != '':
                        anchor = anchor.replace('-', '')
                        anchor = f'https://www.sec.gov/Archives/edgar/data/{cik}/{anchor}/primary_doc.xml'
                        archives_set.add(anchor)

                for link in range(maxResults):
                    r = requests.get(list(archives_set)[link], headers=headers)
                    data = literal_eval(json.dumps(xmltodict.parse(r.text)).replace('null', 'None'))
                    fieldPath = data['edgarSubmission']['formData']['seriesLevelInfo']
                    seriesId = data['edgarSubmission']['formData']['generalInfo'][
                        'seriesId']
                    date = data['edgarSubmission']['formData']['generalInfo'][
                        'reportDate']

                    returnResults.append(
                        [{'Company Name': fieldPath['adviser']['adviserName'],
                          'Entity Type': 'Company'},
                         {uid: {'Resolution': 'Adviser', 'Notes': ''}}])
                    returnResults.append(
                        [{'Company Name': fieldPath['indpPubAccountant']['name'],
                          'Entity Type': 'Company'},
                         {uid: {'Resolution': 'Independent Pub Accountant', 'Notes': ''}}])
                    returnResults.append(
                        [{'Company Name': fieldPath['administrator']['administratorName'],
                          'Entity Type': 'Company'},
                         {uid: {'Resolution': 'Administrator', 'Notes': ''}}])
                    returnResults.append(
                        [{'Company Name': fieldPath['transferAgent']['name'],
                          'Entity Type': 'Company'},
                         {uid: {'Resolution': 'Transfer Agent', 'Notes': ''}}])

                    for value in seriesLevelInfoKeys:
                        returnResults.append(
                            [{'Phrase': f'N-MFP2:({value}) '
                                        + f'ID: {seriesId} Date: {date}',
                              'Notes': fieldPath[value],
                              'Entity Type': 'Phrase'},
                             {uid: {'Resolution': value, 'Notes': ''}}])

                    for value in fieldPath['moneyMarketFundCategory']:
                        returnResults.append(
                            [{'Phrase': value,
                              'Entity Type': 'Phrase'},
                             {uid: {'Resolution': value, 'Notes': ''}}])

                    for field in liquidAssets:
                        if 'Daily' in field:
                            returnResults.append([{'Field Name': f'N-MFP2:({field})' + ' '
                                                                 + f'ID: {seriesId} Date: {date}',
                                                   'Friday 1': fieldPath[field][
                                                       'ns3:fridayDay1'],
                                                   'Friday 2': fieldPath[field][
                                                       'ns3:fridayDay2'],
                                                   'Friday 3': fieldPath[field][
                                                       'ns3:fridayDay3'],
                                                   'Friday 4': fieldPath[field][
                                                       'ns3:fridayDay4'],
                                                   'Friday 5': 'NO Value in Daily Measure',
                                                   'Entity Type': 'FormNMFP2'},
                                                  {uid: {'Resolution': field,
                                                         'Name': 'FormNMFP2',
                                                         'Notes': ''}}])
                        else:
                            returnResults.append([{'Field Name': f'N-MFP2:({field})' + ' '
                                                                 + f'ID: {seriesId} Date: {date}',
                                                   'Friday 1': fieldPath[field][
                                                       'ns3:fridayWeek1'],
                                                   'Friday 2': fieldPath[field][
                                                       'ns3:fridayWeek2'],
                                                   'Friday 3': fieldPath[field][
                                                       'ns3:fridayWeek3'],
                                                   'Friday 4': fieldPath[field][
                                                       'ns3:fridayWeek4'],
                                                   'Friday 5': fieldPath[field][
                                                       'ns3:fridayWeek5'],
                                                   'Entity Type': 'FormNMFP2'},
                                                  {uid: {'Resolution': field,
                                                         'Name': 'FormNMFP2',
                                                         'Notes': ''}}])

                    classLevelInfo = data['edgarSubmission']['formData']['classLevelInfo']
                    for classInfo in classLevelInfo:
                        index_of_child = len(returnResults)
                        returnResults.append(
                            [{'Phrase': classInfo['classesId'],
                              'Entity Type': 'Phrase'},
                             {uid: {'Resolution': 'Classes Id', 'Notes': ''}}])
                        returnResults.append([{'Field Name': f'N-MFP2:(Net Asset Per Share)' + ' '
                                                             + f'ID: {seriesId} Date: {date}',
                                               'Friday 1': classInfo['netAssetPerShare'][
                                                   'ns3:fridayWeek1'],
                                               'Friday 2': classInfo['netAssetPerShare'][
                                                   'ns3:fridayWeek2'],
                                               'Friday 3': classInfo['netAssetPerShare'][
                                                   'ns3:fridayWeek3'],
                                               'Friday 4': classInfo['netAssetPerShare'][
                                                   'ns3:fridayWeek4'],
                                               'Friday 5': classInfo['netAssetPerShare'][
                                                   'ns3:fridayWeek5'],
                                               'Entity Type': 'FormNMFP2'},
                                              {index_of_child: {'Resolution': 'Net Asset Per Share',
                                                                'Name': 'FormNMFP2',
                                                                'Notes': ''}}])
                        for weekCount in range(1, 6):
                            returnResults.append(
                                [{'Phrase': classInfo[f'fridayWeek{weekCount}']['weeklyGrossSubscriptions'],
                                  'Entity Type': 'Phrase'},
                                 {index_of_child: {'Resolution': f'Friday Week {weekCount} Weekly Gross Subscriptions',
                                                   'Notes': ''}}])
                            returnResults.append(
                                [{'Phrase': classInfo[f'fridayWeek{weekCount}']['weeklyGrossRedemptions'],
                                  'Entity Type': 'Phrase'},
                                 {index_of_child: {'Resolution': f'Friday Week {weekCount} Weekly Gross Redemptions',
                                                   'Notes': ''}}])

                        for value in classLevelInfoKeys:
                            returnResults.append(
                                [{'Phrase': classInfo[value],
                                  'Entity Type': 'Phrase'},
                                 {index_of_child: {'Resolution': value,
                                                   'Notes': ''}}])

                    scheduleOfPortfolioSecurities = data['edgarSubmission']['formData']['scheduleOfPortfolioSecuritiesInfo']
                    instance = 0
                    for securitiesInfo in scheduleOfPortfolioSecurities:
                        index_of_child = len(returnResults)
                        returnResults.append(
                            [{'Company Name': securitiesInfo.get('nameOfIssuer') + ' ' + str(instance),
                              'Entity Type': 'Company'},
                             {uid: {'Resolution': 'Issuer', 'Notes': ''}}])
                        instance += 1
                        returnResults.append(
                            [{'CUSIP': securitiesInfo.get('CUSIPMember'),
                              'Entity Type': 'CUSIP'},
                             {index_of_child: {'Resolution': 'CUSIP', 'Notes': ''}}])
                        returnResults.append(
                            [{'LEIID': securitiesInfo.get('LEIID'),
                              'Entity Type': 'LEIID'},
                             {index_of_child: {'Resolution': 'LEIID', 'Notes': ''}}])
                        returnResults.append(
                            [{'ISINID': securitiesInfo.get('ISINId'),
                              'Entity Type': 'ISINID'},
                             {index_of_child: {'Resolution': 'ISINID', 'Notes': ''}}])

                        for value in securitiesInfoKeys:
                            returnResults.append(
                                [{'Phrase': securitiesInfo[value],
                                  'Entity Type': 'Phrase'},
                                 {index_of_child: {'Resolution': value,
                                                   'Notes': ''}}])

                        for value in securitiesInfo['NRSRO']:
                            child_of_child = len(returnResults)
                            returnResults.append(
                                [{'Company Name': value.get('nameOfNRSRO'),
                                  'Entity Type': 'Company'},
                                 {index_of_child: {'Resolution': 'NRSRO',
                                                   'Notes': ''}}])
                            returnResults.append(
                                [{'Phrase': value.get('rating'),
                                  'Entity Type': 'Phrase'},
                                 {child_of_child: {'Resolution': 'Rating',
                                                   'Notes': ''}}])

                        try:
                            collateralIssuer = securitiesInfo['collateralIssuers']
                            for issuer in collateralIssuer:
                                returnResults.append([{'Name': issuer['nameOfCollateralIssuer'],
                                                       'Coupon or Yield': issuer['couponOrYield'],
                                                       'Principal Amount': issuer['principalAmountToTheNearestCent'],
                                                       'Value of Collateral': issuer['valueOfCollateralToTheNearestCent'],
                                                       'Ctgry Investments Rprsnts Collateral':
                                                           issuer['ctgryInvestmentsRprsntsCollateral'],
                                                       'Entity Type': 'Collateral Issuer'},
                                                      {index_of_child: {'Resolution': 'Net Asset Per Share',
                                                                        'Name': 'Collateral Issuer',
                                                                        'Notes': ''}}])

                        except KeyError:
                            continue
            page.close()
            browser.close()
        return returnResults
