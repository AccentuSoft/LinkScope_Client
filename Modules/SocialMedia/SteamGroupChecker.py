#!/usr/bin/env python3


class SteamGroupChecker:
    name = "Steam Groups Search"
    category = "Online Identity"
    description = "Find Steam groups and game hubs whose name matches the input text, plus groups that have the " \
                  "input text in the 'Overview' section of their page. Can use quotes to force exact match, " \
                  "otherwise the input is interpreted as space-delimited keywords."
    originTypes = {'Phrase', 'Social Media Group'}
    resultTypes = {'Social Media Group', 'Website'}
    parameters = {'Max Results': {'description': 'Please enter the maximum number of results to return for each input '
                                                 'entity.',
                                  'type': 'String',
                                  'value': '',
                                  'default': '5'}}

    def resolution(self, entityJsonList, parameters):
        from playwright.sync_api import sync_playwright, TimeoutError, Error
        from bs4 import BeautifulSoup
        from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QSize
        from PySide6.QtGui import QImage
        import requests

        groupSearchURL = 'https://steamcommunity.com/search/groups/#text='

        returnResults = []
        try:
            maxResults = int(parameters['Max Results'])
        except ValueError:
            return "Invalid integer value provided for 'Max Results' parameter."
        if maxResults <= 0:
            return []

        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/101.0.4951.64 Safari/537.36'
            )

            for entity in entityJsonList:
                uid = entity['uid']
                entityType = entity['Entity Type']
                if entityType == 'Phrase':
                    groupName = entity['Phrase']
                elif entityType == 'Social Media Group':
                    groupName = entity['Group Name']
                else:
                    continue

                pageCount = 1
                urlsFound = []
                while len(urlsFound) < maxResults:
                    page = context.new_page()
                    pageURL = groupSearchURL + groupName + '&page=' + str(pageCount)

                    pageResolved = False
                    for _ in range(3):
                        try:
                            page.goto(pageURL, wait_until="networkidle", timeout=10000)
                            pageResolved = True
                            break
                        except TimeoutError:
                            pass
                        except Error:
                            break
                    if not pageResolved:
                        # Last chance for this to work; some pages have issues with the "networkidle" trigger.
                        try:
                            page.goto(pageURL, wait_until="load", timeout=10000)
                        except Error:
                            break

                    pageContents = BeautifulSoup(page.content(), 'lxml')

                    if len(pageContents.find_all('div', {'class': 'search_results_error'})) != 0:
                        break

                    for groupElement in pageContents.find_all('div', {'class': 'search_row group'}):
                        groupAvatarElement = groupElement.findChild('div', {'class': 'search_group_avatar_holder'})
                        if groupAvatarElement is None:
                            groupAvatarElement = groupElement.findChild('div',
                                                                        {'class': 'search_gamegroup_avatar_holder'})
                        groupAvatarImageLink = groupAvatarElement.findChild('img').get('src')
                        groupPageElement = groupElement.findChild('div', {'class': 'searchPersonaInfo'})
                        groupPageElementDetails = groupPageElement.find_all('div')
                        groupPageURL = groupPageElementDetails[0].findChild('a').get('href')
                        groupPageName = groupPageElementDetails[0].findChild('a').text
                        groupType = groupPageElementDetails[0].findChild('span').text.split('- ')[1]
                        groupMemberNumber = groupPageElementDetails[1].findChild('span').text

                        # For some reason, some stuff is considered twice.
                        if groupPageURL in urlsFound:
                            continue
                        else:
                            urlsFound.append(groupPageURL)

                        try:
                            thumbnailIconRequest = requests.get(groupAvatarImageLink)
                            if thumbnailIconRequest.status_code != 200:
                                raise ValueError('Invalid Image / Image not found')
                            thumbnailIconByteArray = QByteArray(thumbnailIconRequest.content)
                            thumbnailIconImageOriginal = QImage().fromData(thumbnailIconByteArray)
                            thumbnailIconImageScaled = thumbnailIconImageOriginal.scaled(QSize(40, 40))
                            thumbnailByteArrayFin = QByteArray()
                            thumbnailImageBuffer = QBuffer(thumbnailByteArrayFin)
                            thumbnailImageBuffer.open(QIODevice.WriteOnly)
                            thumbnailIconImageScaled.save(thumbnailImageBuffer, "PNG")
                            thumbnailImageBuffer.close()
                        except Exception:
                            thumbnailByteArrayFin = None

                        returnResults.append([{'URL': groupPageURL,
                                               'Entity Type': 'Website'},
                                              {uid: {'Resolution': 'Steam Group URL',
                                                     'Notes': ''}}])
                        returnResults.append([{'Group Name': groupPageName,
                                               'Steam Group Members': groupMemberNumber,
                                               'Steam Group Type': groupType,
                                               'Entity Type': 'Social Media Group',
                                               'Icon': thumbnailByteArrayFin},
                                              {len(returnResults) - 1: {'Resolution': 'Steam Group',
                                                                        'Notes': ''}}])

                        if len(urlsFound) >= maxResults:
                            break

                    # Need to close and reopen the page, because the parameter arguments are after a '#', and
                    #   playwright does not recognize the different URLs as actually different.
                    page.close()
                    pageCount += 1

            context.close()
            browser.close()
        return returnResults
