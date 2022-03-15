#!/usr/bin/env python3


class Offshore_Leaks_Entities:
    name = "Offshore Leaks Entities"
    category = "Offshore Leaks"
    description = "Find information about OffShore Entities."
    originTypes = {'Phrase', 'Person', 'Company', 'Organization'}
    resultTypes = {'Company, Country', 'Phrase'}
    parameters = {'Max Results': {'description': 'Please enter the maximum number of results to return. ',
                                  'type': 'String',
                                  'default': '10',
                                  'value': 'Creating a lot of nodes could slow down the software. Please be mindful '
                                           'of the value you enter.'}}

    def resolution(self, entityJsonList, parameters):
        import requests
        import pandas as pd
        from requests_futures.sessions import FuturesSession
        from concurrent.futures import as_completed

        futures = []
        uidList = []
        return_result = []

        url = "https://offshoreleaks.icij.org/"
        try:
            max_results = int(parameters['Max Results'])
        except ValueError:
            return "The value for parameter 'Max Results' is not a valid integer."
        with FuturesSession(max_workers=15) as session:
            for entity in entityJsonList:
                uidList.append(entity['uid'])
                primary_field = entity[list(entity)[1]].strip()
                crafted_url = url + f"search?cat=0&e=&from={max_results}&q={primary_field}&utf8=✓"
                futures.append(session.get(crafted_url))
        for future in as_completed(futures):
            uid = uidList[futures.index(future)]
            try:
                df_list = pd.read_html(future.result().text)
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"
            except ValueError:
                return "We couldn't retrieve any results pls try a different search query."
            df = df_list[0]
            df = df.iloc[:]
            # print(df)
            for company in range(len(df[:max_results])):
                # print(company)
                index_of_child = len(return_result)
                return_result.append([{'Company Name': df['Unnamed: 0'][company],
                                       'Entity Type': 'Company'},
                                      {uid: {'Resolution': 'Offshore Leaks Company', 'Notes': ''}}])
                return_result.append([{'Date': str(df['Incorporation'][company]),
                                       'Entity Type': 'Date'},
                                      {index_of_child: {'Resolution': 'Offshore Leaks', 'Notes': ''}}])
                if df['Jurisdiction'][company] != "Not identified" and df['Jurisdiction'][company] != " Not identified":
                    return_result.append([{'Country Name': str(df['Jurisdiction'][company]),
                                           'Entity Type': 'Country'},
                                          {index_of_child: {'Resolution': 'Jurisdiction', 'Notes': ''}}])
                if df['Data From'][company] != "Not identified" and df['Data From'][company] != " Not identified":
                    return_result.append([{'Phrase': str(df['Data From'][company]),
                                           'Entity Type': 'Phrase'},
                                          {index_of_child: {'Resolution': 'Document', 'Notes': ''}}])
                try:
                    countries = df['Linked To'][company]
                    countries_list = countries.split(",")
                    for country in countries_list:
                        if country != "Not identified" and country != " Not identified":
                            return_result.append([{'Country Name': country,
                                                   'Entity Type': 'Country'},
                                                  {index_of_child: {'Resolution': 'Linked to', 'Notes': ''}}])
                except AttributeError:
                    continue
        return return_result
