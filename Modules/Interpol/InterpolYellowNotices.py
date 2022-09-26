#!/usr/bin/env python3


class InterpolYellowNotices:

    name = "Interpol Yellow Notice Check"
    category = "Crime"
    description = "Find Interpol Yellow Notices about a person. Names from entities must be in the format " \
                  "Firstname Lastname."
    originTypes = {'Phrase', 'Person', 'Politically Exposed Person'}
    resultTypes = {'Yellow Notice'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import requests
        from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QSize
        from PySide6.QtGui import QImage

        firstRequestPart1 = "https://ws-public.interpol.int/notices/v1/yellow?forename="
        firstRequestPart2 = "&ageMax=200&ageMin=0&page="
        firstRequestPart3 = "&resultPerPage=160"

        # Some notices may have missing info as 'null'.
        null = None

        returnResults = []

        def handleYellowNotice(yellowNoticeContents: dict) -> None:
            for yellowNotice in yellowNoticeContents['_embedded']['notices']:
                noticeLink = yellowNotice['_links']['self']['href']

                noticeID = noticeLink.split('/yellow/')[1]

                noticeContentsRaw = requests.get(noticeLink).json()

                # Clean out values that are None as they cause issues with join()
                noticeContents = {k: v for k, v in noticeContentsRaw.items() if v is not None}

                try:
                    thumbnailPictureURL = noticeContents['_links']['thumbnail']['href']
                    thumbnailIconRequest = requests.get(thumbnailPictureURL)
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

                returnResults.append([{'ID': noticeID,
                                       'Forename': noticeContents.get('forename', 'Unknown'),
                                       'Name': noticeContents.get('name', 'Unknown'),
                                       'Gender': noticeContents.get('sex_id', 'Unknown'),
                                       'Date of Birth': noticeContents.get('date_of_birth', 'Unknown'),
                                       'Country of Birth': noticeContents.get('country_of_birth_id', 'Unknown'),
                                       'Place of Birth': noticeContents.get('place_of_birth', 'Unknown'),
                                       'Mother Forename': noticeContents.get('mother_forename', 'Unknown'),
                                       'Mother Name': noticeContents.get('mother_name', 'Unknown'),
                                       'Father Forename': noticeContents.get('father_forename', 'Unknown'),
                                       'Father Name': noticeContents.get('father_name', 'Unknown'),
                                       'Weight': str(noticeContents.get('weight', 'Unknown')),
                                       'Height': str(noticeContents.get('height', 'Unknown')),
                                       'Distinguishing Features': noticeContents.get('distinguishing_marks',
                                                                                     'Unknown'),
                                       'Languages Spoken': ', '.join(noticeContents.get('languages_spoken_ids',
                                                                                        ['Unknown'])),
                                       'Nationalities': ', '.join(noticeContents.get('nationalities',
                                                                                     ['Unknown'])),
                                       'Eye Colors': ', '.join(noticeContents.get('eyes_colors_id',
                                                                                  ['Unknown'])),
                                       'Hair Colors': ', '.join(noticeContents.get('hairs_id',
                                                                                   ['Unknown'])),
                                       'Place Of Event': noticeContents.get('place', 'Unknown'),
                                       'Date Of Event': noticeContents.get('date_of_event', 'Unknown'),
                                       'Entity Type': 'Yellow Notice',
                                       'Date Created': noticeContents.get('date_of_birth', 'Unknown'),
                                       'Icon': thumbnailByteArrayFin},
                                      {uid: {'Resolution': 'Yellow Notice',
                                             'Notes': ''}}])

        for entity in entityJsonList:
            uid = entity['uid']
            entityType = entity['Entity Type']
            if entityType in ['Person', 'Politically Exposed Person']:
                primaryField = entity['Full Name'].strip()
            elif entityType == 'Phrase':
                primaryField = entity['Phrase'].strip()
            else:
                continue

            # We take the first part of the first name and the last part of the last name.
            # This ensures that we will not miss any matches.
            nameFragments = primaryField.split(' ')
            firstName = nameFragments[0].upper()
            lastName = None if len(nameFragments) == 1 else nameFragments[-1].upper()
            firstRequestURL = firstRequestPart1 + firstName
            if lastName is not None:
                firstRequestURL += f"&name={lastName}"
            firstRequestURL += firstRequestPart2

            firstRequest = requests.get(f"{firstRequestURL}1{firstRequestPart3}")

            pageContents = firstRequest.json()
            lastPage = int(pageContents['_links']['last']['href'].split('&page=')[1].split('&')[0])

            handleYellowNotice(pageContents)

            for pageIndex in range(2, lastPage + 1):
                pageContents = requests.get(firstRequestURL + str(pageIndex) + firstRequestPart3)
                handleYellowNotice(pageContents.json())

        return returnResults
