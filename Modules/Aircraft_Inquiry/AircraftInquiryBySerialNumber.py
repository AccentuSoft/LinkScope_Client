#!/usr/bin/env python3


class AircraftInquiryBySerialNumber:
    name = "Aircraft Inquiry By Serial Number"
    category = "Aircraft"
    description = "Find information about aircraft identifications from https://registry.faa.gov/aircraftinquiry/"
    originTypes = {"Identification Number"}
    resultTypes = {'Phrase', 'Company'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import requests
        from requests_futures.sessions import FuturesSession
        from concurrent.futures import as_completed
        import pandas as pd

        futures = []
        uidList = []
        return_result = []

        submit_url = "https://registry.faa.gov/aircraftinquiry/Search/SerialResult"
        with FuturesSession(max_workers=15) as session:
            for entity in entityJsonList:
                uidList.append(entity['uid'])
                futures.append(session.post(submit_url, data={"Serialtxt": entity['ID Number'], "sort_option": "1"}))
        for future in as_completed(futures):
            uid = uidList[futures.index(future)]
            try:
                df_list = pd.read_html(future.result().text)
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"
            except ValueError:
                return "No results retrieved"
            df = df_list[0]
            for index in range(len(df["N-Number"])):
                return_result.append([{'Company Name': df["Manufacturer Name"][index],
                                       'Entity Type': 'Company'},
                                      {uid: {'Resolution': 'Aircraft Manufacturer', 'Notes': ''}}])
                return_result.append([{'Phrase': df["N-Number"][index],
                                       'Entity Type': 'Phrase'},
                                      {uid: {'Resolution': 'Aircraft N-Number', 'Notes': ''}}])
                return_result.append([{'Phrase': df["Model"][index],
                                       'Entity Type': 'Phrase'},
                                      {uid: {'Resolution': 'Aircraft Model', 'Notes': ''}}])
        return return_result
