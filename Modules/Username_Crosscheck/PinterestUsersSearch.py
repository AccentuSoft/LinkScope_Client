#!/usr/bin/env python3


class PinterestUsersSearch:
    name = "Pinterest People Search"
    category = "Online Identity"
    description = "Use Pinterest's search to find user profiles using Email Addresses, Phone Numbers or Phrases."
    originTypes = {'Email Address', 'Phrase', 'Phone Number'}
    resultTypes = {'Social Media Handle'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        from playwright.sync_api import sync_playwright, Error
        from time import sleep
        from bs4 import BeautifulSoup
        from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QSize
        from PySide6.QtGui import QImage
        from random import random
        import requests

        baseURL = "https://www.pinterest.com/search/users/?q="

        returnResults = []

        with sync_playwright() as p:
            browser = p.firefox.launch()
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            try:
                page.goto(baseURL)
            except Error:
                return "Error occurred when trying to navigate to Pinterest."

            for entity in entityJsonList:
                uid = entity['uid']
                primaryField = entity[list(entity)[1]]

                try:
                    page.goto(baseURL + primaryField, wait_until="networkidle", timeout=60000)
                    # Wait until everything is 100% loaded, just in case.
                    sleep(10)

                    soup = BeautifulSoup(page.content(), "lxml")
                    listElements = soup.find_all(attrs={'role': 'listitem'})

                    for listElement in listElements:
                        username = listElement.find('a')['href'][1:-1]
                        href = "https://www.pinterest.com/" + username + "/"
                        imgElement = listElement.find('img')
                        textStrings = listElement.findAll(text=True)
                        prettyName = textStrings[0]
                        followerNumber = textStrings[1]

                        childIconByteArrayFin = None
                        if imgElement:
                            try:
                                childPinterestAccIconRequest = requests.get(imgElement['src'])
                                childIconByteArray = QByteArray(childPinterestAccIconRequest.content)
                                childIconImageOriginal = QImage().fromData(childIconByteArray)
                                childIconImageScaled = childIconImageOriginal.scaled(QSize(40, 40))
                                childIconByteArrayFin = QByteArray()
                                childImageBuffer = QBuffer(childIconByteArrayFin)
                                childImageBuffer.open(QIODevice.WriteOnly)
                                childIconImageScaled.save(childImageBuffer, "PNG")
                                childImageBuffer.close()
                            except Exception:
                                childIconByteArrayFin = None

                        returnResults.append([{'User Name': username,
                                               'Pretty Name': prettyName,
                                               'Profile URL': href,
                                               'Instagram Followers': followerNumber,
                                               'Entity Type': 'Social Media Handle',
                                               'Icon': childIconByteArrayFin},
                                              {uid: {'Resolution': 'Account Found',
                                                     'Notes': ''}}])
                except Error:
                    pass

            # Wait a bit before moving on to the next query.
            sleep(2 + random())

        return returnResults
