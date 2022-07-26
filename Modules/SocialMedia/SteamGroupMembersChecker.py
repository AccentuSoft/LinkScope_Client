#!/usr/bin/env python3


class SteamGroupMembersChecker:
    name = "Get Steam Group Members"
    category = "Online Identity"
    description = "Get all Steam Social Media accounts belonging to a Steam Group."
    originTypes = {'Website'}
    resultTypes = {'Social Media Handle', 'Website'}
    parameters = {'Max Results': {'description': 'Please enter the Maximum number of Results to return for each input '
                                                 'entity.',
                                  'type': 'String',
                                  'value': '',
                                  'default': '5'}}

    def resolution(self, entityJsonList, parameters):
        from playwright.sync_api import sync_playwright, TimeoutError, Error
        from bs4 import BeautifulSoup
        from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QSize
        from PySide6.QtGui import QImage
        from json import loads
        import requests

        gamesMembersBaseURL = 'https://steamcommunity.com/games/'

        returnResults = []
        try:
            maxResults = int(parameters['Max Results'])
        except ValueError:
            return "Invalid integer value provided for 'Max Results' parameter."
        if maxResults <= 0:
            return []

        def addResult(rank, username, pageLink, avatarLink) -> None:
            try:
                thumbnailIconRequest = requests.get(avatarLink)
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

            returnResults.append([{'URL': pageLink,
                                   'Entity Type': 'Website'},
                                  {uid: {'Resolution': 'Steam User Page URL',
                                         'Notes': ''}}])
            returnResults.append([{'User Name': username,
                                   'User Rank': rank,
                                   'Entity Type': 'Social Media Handle',
                                   'Icon': thumbnailByteArrayFin},
                                  {len(returnResults) - 1: {'Resolution': 'Steam User',
                                                            'Notes': ''}}])

        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/101.0.4951.64 Safari/537.36'
            )
            page = context.new_page()

            for entity in entityJsonList:
                uid = entity['uid']
                groupURL = entity['URL']

                if not groupURL.startswith('https://steamcommunity.com/'):
                    # Ignore non-steam group URLs.
                    continue
                if groupURL.startswith('https://steamcommunity.com/groups/'):
                    membersURL = groupURL + '/members'
                else:
                    for _ in range(3):
                        try:
                            page.goto(groupURL, wait_until="networkidle", timeout=10000)
                            pageResolved = True
                            break
                        except TimeoutError:
                            pass
                        except Error:
                            break
                    if not pageResolved:
                        # Last chance for this to work; some pages have issues with the "networkidle" trigger.
                        try:
                            page.goto(groupURL, wait_until="load", timeout=10000)
                        except Error:
                            continue
                    try:
                        # If we get a warning about age restriction, click the checkbox and view the actual page.
                        # Click text=Don't warn me again for
                        page.locator("text=Don't warn me again for").click()
                        # Click text=View Page
                        page.locator("text=View Page").click()
                    except Error:
                        pass

                    appPage = BeautifulSoup(page.content(), 'lxml')
                    appPageDataConfig = appPage.findChild('div', {'id': 'application_config'}).get('data-community')
                    appPageVanityID = loads(appPageDataConfig)["VANITY_ID"]
                    membersURL = gamesMembersBaseURL + appPageVanityID + '/members'

                pageCount = 1
                urlsFound = []
                while len(urlsFound) < maxResults:
                    pageURL = membersURL + '/?p=' + str(pageCount)

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
                    memberList = pageContents.findChild('div', {'id': 'memberList'})

                    if len(memberList) == 3:
                        break

                    # Member blocks in regular groups, friend blocks in game groups.
                    memberBlocks = pageContents.select("div[class^=member_block ]")
                    friendBlocks = pageContents.select("div[class^=friendBlock]")

                    for groupElement in memberBlocks:
                        userURL = groupElement.findChild('a', {'class': 'linkFriend'})['href']
                        if userURL.startswith('https://steamcommunity.com/id/'):
                            userID = userURL.split('https://steamcommunity.com/id/', 1)[1]
                        else:
                            userID = userURL.split('https://steamcommunity.com/profiles/', 1)[1]

                        if userURL == 'https://steamcommunity.com/profiles/76561198067124199':
                            # Placeholder user by Steam.
                            continue
                        elif userURL in urlsFound:
                            continue
                        else:
                            urlsFound.append(userURL)

                        superMemberBlock = groupElement.findChild('div', {'class': 'rank_icon'})
                        if superMemberBlock is not None:
                            memberTitle = superMemberBlock['title']
                        else:
                            memberTitle = 'No rank / No special privileges'
                        userAvatarLink = groupElement.find_all('img')[-1]['src']

                        addResult(memberTitle, userID, userURL, userAvatarLink)

                        if len(urlsFound) >= maxResults:
                            break

                    for groupElement in friendBlocks:
                        avatarDiv = groupElement.findChild('div', {'class': 'avatarIcon'})
                        userURLElement = avatarDiv.findChild('a')
                        userURL = userURLElement['href']
                        if userURL.startswith('https://steamcommunity.com/id/'):
                            userID = userURL.split('https://steamcommunity.com/id/', 1)[1]
                        else:
                            userID = userURL.split('https://steamcommunity.com/profiles/', 1)[1]

                        if userURL == 'https://steamcommunity.com/profiles/76561198067124199':
                            # Placeholder user by Steam.
                            continue
                        elif userURL in urlsFound:
                            continue
                        else:
                            urlsFound.append(userURL)

                        superMemberBlock = groupElement.findChild('img', {'class': 'officerIcon'})
                        if superMemberBlock is not None:
                            memberTitle = superMemberBlock['src'].split('/')[-1].split('.gif')[0].split('rankIcon')[1]
                        else:
                            memberTitle = 'No rank / No special privileges'

                        userAvatarLink = userURLElement.findChild('img')['src']

                        addResult(memberTitle, userID, userURL, userAvatarLink)

                        if len(urlsFound) >= maxResults:
                            break

                    pageCount += 1

            page.close()
            context.close()
            browser.close()
        return returnResults
