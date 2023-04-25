#!/usr/bin/env python3


class SteamUsernameChecker:
    name = "Steam Users Search"
    category = "Online Identity"
    description = "Find the profiles of Steam users whose username matches the input text."
    originTypes = {'Phrase', 'Person', 'Politically Exposed Person', 'Social Media Handle'}
    resultTypes = {'Social Media Handle', 'Website'}
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

        userSearchURL = 'https://steamcommunity.com/search/users/#text='

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
                if entityType in ['Person', 'Politically Exposed Person']:
                    groupName = entity['Full Name']
                elif entityType == 'Phrase':
                    groupName = entity['Phrase']
                elif entityType == 'Social Media Handle':
                    groupName = entity['User Name']
                else:
                    continue

                pageCount = 1
                urlsFound = []
                while len(urlsFound) < maxResults:
                    page = context.new_page()
                    pageURL = userSearchURL + groupName + '&page=' + str(pageCount)

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
                    for userElement in pageContents.find_all('div', {'class': 'search_row'}):
                        userPageElement = userElement.findChild('div', {'class': 'searchPersonaInfo'})
                        userPageElementIDDetails = userPageElement.findChild('a')
                        userURL = userPageElementIDDetails['href']
                        if userURL.startswith('https://steamcommunity.com/id/'):
                            userID = userURL.split('https://steamcommunity.com/id/', 1)[1]
                        else:
                            userID = userURL.split('https://steamcommunity.com/profiles/', 1)[1]

                        if (
                            userURL == 'https://steamcommunity.com/profiles/76561198067124199'  # Steam Placeholder user
                            or userURL in urlsFound
                        ):
                            continue
                        else:
                            urlsFound.append(userURL)

                        userAvatarElement = userElement.findChild('div', {'class': 'avatarMedium'})
                        userAvatarImageLink = userAvatarElement.findChild('img')['src']

                        try:
                            thumbnailIconRequest = requests.get(userAvatarImageLink)
                            if thumbnailIconRequest.status_code != 200:
                                raise ValueError('Invalid Image / Image not found')
                            thumbnailIconByteArray = QByteArray(thumbnailIconRequest.content)
                            thumbnailIconImageOriginal = QImage().fromData(thumbnailIconByteArray)
                            thumbnailIconImageScaled = thumbnailIconImageOriginal.scaled(QSize(40, 40))
                            thumbnailByteArrayFin = QByteArray()
                            thumbnailImageBuffer = QBuffer(thumbnailByteArrayFin)
                            thumbnailImageBuffer.open(QIODevice.OpenModeFlag.WriteOnly)
                            thumbnailIconImageScaled.save(thumbnailImageBuffer, "PNG")
                            thumbnailImageBuffer.close()
                        except Exception:
                            thumbnailByteArrayFin = None

                        returnResults.append([{'URL': userURL,
                                               'Entity Type': 'Website'},
                                              {uid: {'Resolution': 'Steam User Profile URL',
                                                     'Notes': ''}}])
                        returnResults.append([{'User Name': userID,
                                               'Entity Type': 'Social Media Handle',
                                               'Icon': thumbnailByteArrayFin},
                                              {len(returnResults) - 1: {'Resolution': 'Steam User',
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
