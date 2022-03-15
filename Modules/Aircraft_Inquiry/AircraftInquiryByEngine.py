#!/usr/bin/env python3


class AircraftInquiryByEngine:
    name = "Aircraft Inquiry By Engine"
    category = "Aircraft"
    description = "Find information about aircraft identifications from https://registry.faa.gov/aircraftinquiry/"
    originTypes = {"Phrase"}
    resultTypes = {"Phrase"}
    parameters = {'Manufacturer': {'description': "Enter the Manufacturer of the Engine Model",
                                   'type': 'String',
                                   'value': 'None'}}

    def resolution(self, entityJsonList, parameters):
        import requests
        from requests_futures.sessions import FuturesSession
        from concurrent.futures import as_completed
        import pandas as pd

        Manufacturer = parameters['Manufacturer']

        futures = []
        uidList = []
        return_result = []

        submit_url = "https://registry.faa.gov/aircraftinquiry/Search/"
        crafted_url = f"{submit_url}EngineReferenceResult"
        with FuturesSession(max_workers=15) as session:
            for entity in entityJsonList:
                uidList.append(entity['uid'])
                futures.append(session.post(crafted_url, data={"Modeltxt": entity['Phrase'],
                                                               "MfrNametxt": Manufacturer}))
        for future in as_completed(futures):
            uid = uidList[futures.index(future)]
            try:
                df_list = pd.read_html(future.result().text)
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"
            except ValueError:
                return "No results retrieved"
            df = df_list[0]
            return_result.append([{'Phrase': f"Model Code:str({df['Mfr/Mdl Code']})",
                                   'Entity Type': 'Phrase'},
                                  {uid: {'Resolution': 'Aircraft Model Code', 'Notes': ''}}])
            return_result.append([{'Phrase': f"Engine Type:{df['Type Engine']}",
                                   'Entity Type': 'Phrase'},
                                  {uid: {'Resolution': 'Aircraft Engine Type', 'Notes': ''}}])
            return_result.append([{'Phrase': f"Horse Power:str({df['Horsepower']})",
                                   'Entity Type': 'Phrase'},
                                  {uid: {'Resolution': 'Aircraft Engine Horsepower', 'Notes': ''}}])
        return return_result
