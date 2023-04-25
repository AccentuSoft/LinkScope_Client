#!/usr/bin/env python3


class Offshore_Leaks_Entities:
    name = "Offshore Leaks Entities"
    category = "Offshore Leaks"
    description = "Find information about OffShore Entities."
    originTypes = {'Phrase', 'Person', 'Company', 'Organization'}
    resultTypes = {'Company, Country', 'Phrase'}
    parameters = {'Max Results': {'description': 'Please enter the maximum number of results to return per input '
                                                 'entity. Note that these are the number of results that will be '
                                                 'processed from Offshore Leaks - if there are duplicates in the '
                                                 'data set, less results may be returned.',
                                  'type': 'String',
                                  'default': '50',
                                  'value': 'Creating a lot of nodes could slow down the software. Please be mindful '
                                           'of the value you enter.'}}

    def resolution(self, entityJsonList, parameters):
        import requests
        import math
        import pandas as pd
        from time import sleep

        return_result = []

        url = "https://offshoreleaks.icij.org/"
        try:
            max_results = int(parameters['Max Results'])
        except ValueError:
            return "The value for parameter 'Max Results' is not a valid integer."

        if max_results <= 0:
            return []

        nextHundred = math.ceil(max_results / 100) * 100
        for entity in entityJsonList:
            uid = entity['uid']
            primary_field = entity[list(entity)[1]].strip()
            df_list = []
            for batch in range(0, nextHundred, 100):
                crafted_url = f"{url}search?cat=0&from={batch}&q={primary_field}&utf8=✓"
                try:
                    r = requests.get(crafted_url)
                    df_list.append(pd.read_html(r.text)[0])
                except requests.exceptions.ConnectionError:
                    break
                except ValueError:
                    break
                sleep(1)

            df_full = pd.concat(df_list, ignore_index=True)

            try:
                df_part = df_full.head(max_results)
            except IndexError:
                df_part = df_full

            for entry in range(len(df_part)):
                index_of_child = len(return_result)
                return_result.append([{'Company Name': df_part['Entity'][entry].upper(),
                                       'Entity Type': 'Company'},
                                      {uid: {'Resolution': 'Offshore Leaks Entity', 'Notes': ''}}])
                if isinstance(df_part['Data from'][entry], str) and \
                            "not identified" not in df_part['Data from'][entry].lower():
                    return_result.append([{'Phrase': df_part['Data from'][entry],
                                           'Entity Type': 'Phrase'},
                                          {index_of_child: {'Resolution': 'Offshore Leaks Leak', 'Notes': ''}}])
                try:
                    countries = df_part['Linked to'][entry]
                    if isinstance(countries, str) and "not identified" not in countries.lower():
                        countries_list = countries.split(",")
                        for country in countries_list:
                            return_result.append([{'Country Name': country,
                                                   'Entity Type': 'Country'},
                                                  {index_of_child: {'Resolution': 'Linked to', 'Notes': ''}}])
                except AttributeError:
                    continue
                try:
                    countries = df_part['Jurisdiction'][entry]
                    if isinstance(countries, str) and "not identified" not in countries.lower():
                        countries_list = countries.split(",")
                        for country in countries_list:
                            return_result.append([{'Country Name': country,
                                                   'Entity Type': 'Country'},
                                                  {index_of_child: {'Resolution': 'Jurisdiction', 'Notes': ''}}])
                except AttributeError:
                    continue
        return return_result
