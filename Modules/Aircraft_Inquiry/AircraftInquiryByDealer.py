#!/usr/bin/env python3


class AircraftInquiryByDealer:
    name = "Aircraft Inquiry By Dealer"
    category = "Aircraft"
    description = "Find information about aircraft identifications from https://registry.faa.gov/aircraftinquiry/"
    originTypes = {"Company"}
    resultTypes = {'Phrase', 'Company'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import requests
        import pandas as pd
        from requests_futures.sessions import FuturesSession
        from concurrent.futures import as_completed

        futures = []
        uidList = []
        return_result = []

        submit_url = "https://registry.faa.gov/aircraftinquiry/Search/DealerResult"
        with FuturesSession(max_workers=15) as session:
            for entity in entityJsonList:
                uidList.append(entity['uid'])
                futures.append(session.post(submit_url, data={"Dealertxt": entity['Company Name']}))
            for future in as_completed(futures):
                uid = uidList[futures.index(future)]
                try:
                    df_list = pd.read_html(future.result().text)
                except requests.exceptions.ConnectionError:
                    return "Please check your internet connection"
                except ValueError:
                    return "Error occurred when checking the data returned from the endpoint."
                df = df_list[0]
                for certificate_index in range(len(df["Certificate Number"])):
                    index_of_child = len(return_result)
                    return_result.append([{'Company Name': df["Name"][certificate_index],
                                           'Entity Type': 'Company'},
                                          {uid: {'Resolution': 'Aircraft Dealer', 'Notes': ''}}])
                    return_result.append([{'Phrase': df["Certificate Number"][certificate_index],
                                           'Entity Type': 'Phrase'},
                                          {index_of_child: {'Resolution': 'Aircraft Certificate Number', 'Notes': ''}}])
        return return_result
