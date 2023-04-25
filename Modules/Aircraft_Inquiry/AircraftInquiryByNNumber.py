#!/usr/bin/env python3


class AircraftInquiryByNNumber:
    name = "Aircraft Inquiry By N-Number"
    category = "Aircraft"
    description = "Find information about aircraft identifications from https://registry.faa.gov/aircraftinquiry/"
    originTypes = {"Phrase"}
    resultTypes = {'Phrase', 'Person', 'Identification Number', 'Company', 'Country', 'City'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import requests
        from requests_futures.sessions import FuturesSession
        from concurrent.futures import as_completed
        import pandas as pd

        futures = []
        uidList = []
        return_result = []

        submit_url = "https://registry.faa.gov/aircraftinquiry/Search/NNumberResult"
        with FuturesSession(max_workers=15) as session:
            for entity in entityJsonList:
                uidList.append(entity['uid'])
                futures.append(session.post(submit_url, data={"NNumbertxt": entity['Phrase']}))
        for future in as_completed(futures):
            uid = uidList[futures.index(future)]
            try:
                df_list = pd.read_html(future.result().text)
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"
            except ValueError:
                return "No results retrieved"
            df1 = df_list[0]
            df2 = df_list[1]
            df3 = df_list[2]
            return_result.append([{'ID Number': df1[1][0],
                                   'Entity Type': 'Identification Number'},
                                  {uid: {'Resolution': 'Aircraft Identification Number', 'Notes': ''}}])
            return_result.append([{'Company Name': df1[1][1],
                                   'Entity Type': 'Company'},
                                  {uid: {'Resolution': 'Aircraft Company', 'Notes': ''}}])
            return_result.append([{'Full Name': df2[1][0],
                                   'Entity Type': 'Person'},
                                  {uid: {'Resolution': 'Aircraft Owner', 'Notes': ''}}])
            return_result.append([{'City Name': df2[1][2],
                                   'Entity Type': 'City'},
                                  {uid: {'Resolution': "Aircraft Owner's City", 'Notes': ''}}])
            return_result.append([{'Country Name': df2[1][4],
                                   'Entity Type': 'Country'},
                                  {uid: {'Resolution': "Aircraft Owner's Country", 'Notes': ''}}])
            return_result.append([{'Phrase': df3[1][1],
                                   'Entity Type': 'Phrase'},
                                  {uid: {'Resolution': "Aircraft Engine Series", 'Notes': ''}}])
            return_result.append([{'Phrase': df3[1][2],
                                   'Entity Type': 'Phrase'},
                                  {uid: {'Resolution': "Aircraft Engine Motor", 'Notes': ''}}])
        return return_result
