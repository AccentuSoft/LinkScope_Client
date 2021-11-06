#!/usr/bin/env python3


class AircraftInquiryByPersonName:
    name = "Aircraft Inquiry By Person Name"
    description = "Find information about aircraft identifications from https://registry.faa.gov/aircraftinquiry/"
    originTypes = {"Person"}
    resultTypes = {'Phrase', 'Person', 'Identification Number', 'Company'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import requests
        from requests_futures.sessions import FuturesSession
        from concurrent.futures import as_completed
        import pandas as pd

        futures = []
        uidList = []
        return_result = []

        submit_url = "https://registry.faa.gov/aircraftinquiry/Search/"
        crafted_url = f"{submit_url}NameResult"
        with FuturesSession(max_workers=15) as session:
            for entity in entityJsonList:
                uidList.append(entity['uid'])
                futures.append(session.post(crafted_url, data={"nametxt": entity['Full Name'], "sort_option": "1"}))
        for future in as_completed(futures):
            uid = uidList[futures.index(future)]
            try:
                df_list = pd.read_html(future.result().text)
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"
            except ValueError:
                return "No results retrieved"
            df = df_list[0]
            for i in range(len(df["N-Number"])):
                return_result.append([{'Phrase': df["N-Number"][0],
                                       'Entity Type': 'Phrase'},
                                      {uid: {'Resolution': 'Aircraft N-Number', 'Notes': ''}}])
                return_result.append([{'ID Number': str(df['Serial Number'][0]),
                                       'Entity Type': 'Identification Number'},
                                      {uid: {'Resolution': 'Aircraft Identification Number', 'Notes': ''}}])
                return_result.append([{'Company Name': df['Manufacturer Name Model'][0],
                                       'Entity Type': 'Company'},
                                      {uid: {'Resolution': 'Aircraft Manufacturer Name', 'Notes': ''}}])
        return return_result
