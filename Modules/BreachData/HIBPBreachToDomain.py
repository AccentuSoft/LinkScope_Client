#!/usr/bin/env python3


class HIBPBreachToDomain:

    name = "HIBP Breach To Domain"
    category = "Leaked Data"
    description = "Get the domain of the primary website that a data breach occurred on."
    originTypes = {'Data Breach'}
    resultTypes = {'Domain'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):

        returnResults = []

        for entity in entityJsonList:
            domainMaybe = entity.get('Breach Domain')
            if isinstance(domainMaybe, str) and domainMaybe.strip() != '':
                returnResults.append([{'Domain Name': domainMaybe,
                                       'Entity Type': 'Domain'},
                                      {entity['uid']: {'Resolution': 'Data Breach to Domain',
                                                       'Notes': ''}}])

        return returnResults
