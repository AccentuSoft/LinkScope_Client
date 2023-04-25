#!/usr/bin/env python3


class SteamUsernameAliasChecker:
    name = "Get Steam User Aliases"
    category = "Online Identity"
    description = "Find the aliases of Steam users, given links to their profiles."
    originTypes = {'Website'}
    resultTypes = {'Social Media Handle', 'Phrase'}
    parameters = {'Max Results': {'description': 'Please enter the maximum number of results to return for each input '
                                                 'entity.',
                                  'type': 'String',
                                  'value': '',
                                  'default': '5'}}

    def resolution(self, entityJsonList, parameters):
        import requests

        returnResults = []

        try:
            maxResults = int(parameters['Max Results'])
        except ValueError:
            return "Invalid integer value provided for 'Max Results' parameter."
        if maxResults <= 0:
            return []

        for entity in entityJsonList:
            uid = entity['uid']
            entityURL = entity['URL']
            # Ignore links that don't point to Steam user URLs.
            if entityURL.startswith('https://steamcommunity.com/id/'):
                userID = entityURL.split('https://steamcommunity.com/id/', 1)[1]
            elif entityURL.startswith('https://steamcommunity.com/profiles/'):
                userID = entityURL.split('https://steamcommunity.com/profiles/', 1)[1]
            else:
                continue

            aliasURL = f'{entityURL}/ajaxaliases'

            aliases = requests.get(aliasURL).json()
            newHandleIndex = len(returnResults)
            returnResults.append([{'User Name': userID,
                                   'Entity Type': 'Social Media Handle'},
                                  {uid: {'Resolution': 'Steam User',
                                         'Notes': ''}}])
            for alias in aliases[:maxResults]:
                newName = alias['newname']
                timeChanged = alias['timechanged'].replace('@ ', '')

                returnResults.append([{'Phrase': newName,
                                       'Entity Type': 'Phrase',
                                       'Date Created': timeChanged},
                                      {newHandleIndex: {'Resolution': 'Steam User Alias',
                                                        'Notes': ''}}])

        return returnResults
