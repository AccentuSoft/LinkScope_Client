#!/usr/bin/env python3

"""
Credit to: https://github.com/JustAnotherArchivist/snscrape

Output reference:

{"_type": "snscrape.modules.twitter.Tweet",
"url": "https://twitter.com/accentusoft/status/1491141777361113088",
"date": "2022-02-08T20:07:58+00:00",
"content": "Hello World! Version 1 of LinkScope Client has just been released! Have a look and tell us
what you think: \nhttps://t.co/LiVcY2N5O7\n\n#OSINT #OpenSource #LinkScope",
"renderedContent": "Hello World! Version 1 of LinkScope Client has just been released! Have a look and tell
us what you think: \ngithub.com/AccentuSoft/Li\u2026\n\n#OSINT #OpenSource #LinkScope",
"id": 1491141777361113088, "user": {"_type": "snscrape.modules.twitter.User", "username": "accentusoft",
"id": 1457461982563606528, "displayname": "AccentuSoft AccentuSoft", "description": "",
"rawDescription": "", "descriptionUrls": null, "verified": false, "created": "2021-11-07T21:36:51+00:00",
"followersCount": 0, "friendsCount": 44, "statusesCount": 1, "favouritesCount": 2, "listedCount": 0,
"mediaCount": 0, "location": "", "protected": false, "linkUrl": null, "linkTcourl": null,
"profileImageUrl": "https://pbs.twimg.com/profile_images/1457462076872577026/R73cgLK3_normal.png",
"profileBannerUrl": null, "label": null, "url": "https://twitter.com/accentusoft"}, "replyCount": 0,
"retweetCount": 2, "likeCount": 1, "quoteCount": 0, "conversationId": 1491141777361113088, "lang": "en",
"source": "<a href=\"https://mobile.twitter.com\" rel=\"nofollow\">Twitter Web App</a>",
"sourceUrl": "https://mobile.twitter.com", "sourceLabel": "Twitter Web App",
"outlinks": ["https://github.com/AccentuSoft/LinkScope_Client"], "tcooutlinks": ["https://t.co/LiVcY2N5O7"],
"media": null, "retweetedTweet": null, "quotedTweet": null, "inReplyToTweetId": null, "inReplyToUser": null,
"mentionedUsers": null, "coordinates": null, "place": null,
"hashtags": ["OSINT", "OpenSource", "LinkScope"], "cashtags": null}
"""


class TwitterUser:
    name = "Get Tweets by User"

    description = "Get Tweets made by the specified twitter username / handle, or twitter user ID."

    originTypes = {'Social Media Handle', 'Phrase', 'Twitter User'}

    resultTypes = {'Phrase'}

    parameters = {'Username or User ID': {'description': 'Please specify whether to treat the given inputs as '
                                                         'Twitter usernames or as twitter user IDs.\nA Username, or '
                                                         '"twitter handle" in this case, looks like this: "@example", '
                                                         'whereas a user ID is a long series of numbers.',
                                          'type': 'SingleChoice',
                                          'value': {'Usernames', 'User IDs'},
                                          'default': 'Usernames'},
                  'Max Results': {'description': 'Please enter the maximum number of results to return, or "0" to '
                                                 'return all results.',
                                  'type': 'String',
                                  'default': '100'},
                  'Start Date': {'description': 'Please specify the earliest date to retrieve results from.\nThe date '
                                                'format is flexible, but the best formatting for input is:\n'
                                                'YYYY-MM-DD HH:mm:SS Z\nIf you do not wish to specify a date, enter '
                                                '"NONE" (without quotes) in the input box.\nPlease be careful not to '
                                                'use ambiguous formatting such as "1/2/10" or "2022", as the '
                                                'assumptions made by the software may not be what you expect.',
                                 'type': 'String',
                                 'default': 'NONE'}
                  }

    def resolution(self, entityJsonList, parameters):
        import argparse
        import logging
        import requests
        import pytz
        import snscrape.base
        import snscrape.modules
        import snscrape.version
        from dateutil.parser import parse
        from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QSize
        from PySide6.QtGui import QImage

        logging.getLogger().setLevel(60)  # Do not allow any logging

        classes = snscrape.base.Scraper.__subclasses__()
        scrapers = {}
        for cls in classes:
            if cls.name is not None:
                scrapers[cls.name] = cls
            classes.extend(cls.__subclasses__())

        arguments = argparse.Namespace(citation=None, verbosity=0, dumpLocals=False, retries=3, maxResults=None,
                                       format=None, jsonl=True, withEntity=False, since=None, progress=False,
                                       scraper='twitter-user', isUserId=False, username='')

        if parameters['Username or User ID'] == 'User IDs':
            arguments.isUserId = True
        try:
            maxResults = int(parameters['Max Results'])
            if maxResults < 0:
                raise ValueError('')
            if maxResults != 0:
                arguments.maxResults = maxResults
        except ValueError:
            return 'Invalid integer specified for "Max Results" parameter.'

        if parameters['Start Date'] != 'NONE':
            try:
                sinceDate = parse(parameters['Start Date'])
                if sinceDate.tzinfo is None:
                    sinceDate = sinceDate.replace(tzinfo=pytz.UTC)
                arguments.since = sinceDate
            except ValueError:
                return 'Invalid date specified for "Start Date" parameter.'

        returnResults = []
        childIndex = 0

        for entity in entityJsonList:
            uid = entity['uid']
            if entity['Entity Type'] == 'Phrase':
                primaryField = entity['Phrase']
            elif entity['Entity Type'] == 'Twitter User':
                primaryField = entity['Twitter Handle']
            else:
                primaryField = entity['User Name']
            if primaryField.startswith('@'):
                primaryField = primaryField[1:]
            arguments.username = primaryField

            scraper = scrapers['twitter-user'].cli_from_args(arguments)

            for index, item in enumerate(scraper.get_items(), start=1):
                if arguments.since is not None and item.date < arguments.since:
                    break
                if index == 1:
                    # User will be the same for all tweets of the same entity, so no sense in adding it multiple times.
                    childIndex = len(returnResults)
                    try:
                        twitterAccIconRequest = requests.get(item.user.profileImageUrl)
                        iconByteArray = QByteArray(twitterAccIconRequest.content)
                        iconImageOriginal = QImage().fromData(iconByteArray)
                        iconImageScaled = iconImageOriginal.scaled(QSize(40, 40))
                        iconByteArrayFin = QByteArray()
                        imageBuffer = QBuffer(iconByteArrayFin)
                        imageBuffer.open(QIODevice.WriteOnly)
                        iconImageScaled.save(imageBuffer, "PNG")
                        imageBuffer.close()
                    except Exception:
                        iconByteArrayFin = None
                    returnResults.append([{'Twitter Handle': '@' + item.user.username,
                                           'User ID': str(item.user.id),
                                           'User URL': item.user.url,
                                           'Verified': str(item.user.verified),
                                           'Display Name': item.user.displayname,
                                           'Location': item.user.location,
                                           'Description': item.user.description,
                                           'Protected': str(item.user.protected),
                                           'Followers': str(item.user.followersCount),
                                           'Following': str(item.user.friendsCount),
                                           'Statuses': str(item.user.statusesCount),
                                           'Favourites': str(item.user.favouritesCount),
                                           'Listed': str(item.user.listedCount),
                                           'Media': str(item.user.mediaCount),
                                           'Entity Type': 'Twitter User',
                                           'Icon': iconByteArrayFin,  # If None, it will have the pic for Twitter User
                                           'Date Created': item.user.created.isoformat()},
                                          {uid: {'Resolution': 'Twitter User'}}])
                returnResults.append([{'Tweet ID': str(item.id),
                                       'Tweet URL': item.url,
                                       'Replies': str(item.replyCount),
                                       'Retweets': str(item.retweetCount),
                                       'Likes': str(item.likeCount),
                                       'Quotes': str(item.quoteCount),
                                       'Coordinates': str(item.coordinates),
                                       'Place': str(item.place),
                                       'Entity Type': 'Tweet',
                                       'Date Created': item.date.isoformat(),
                                       'Notes': item.content},
                                      {childIndex: {'Resolution': 'Tweet'}}])
                if maxResults and index >= maxResults:
                    break

        return returnResults
