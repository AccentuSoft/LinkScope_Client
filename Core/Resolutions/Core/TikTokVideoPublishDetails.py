#!/usr/bin/env python3


class TikTokVideoPublishDetails:
    # A string that is treated as the name of this resolution.
    name = "TikTok Video Publishing Details"

    category = "Website Information"

    # A string that describes this resolution.
    description = "Extracts information from public TikTok Videos."

    originTypes = {'Website'}

    resultTypes = {'Social Media Handle', 'Date'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        from datetime import datetime

        returnResults = []

        for entity in entityJsonList:
            uid = entity['uid']
            url = entity['URL'].lower()

            try:
                splitURL = url.split('/')
                username = splitURL[3]
                videoID = int(splitURL[5].split('?')[0])
            except (IndexError, ValueError):
                continue

            binString = "{0:b}".format(videoID)
            if len(binString) == 63:
                binString = f'0{binString}'
            binString = int(binString[:32], 2)

            UTCTimestamp = f'{datetime.utcfromtimestamp(binString).isoformat()}+00:00'

            returnResults.extend(([{'Date': UTCTimestamp, 'Entity Type': 'Date'},
                                   {uid: {'Resolution': 'Video Publish Date', 'Notes': ''}}],
                                  [{'User Name': username, 'Entity Type': 'Social Media Handle'},
                                   {uid: {'Resolution': 'Published By', 'Notes': ''}}]))

        return returnResults
