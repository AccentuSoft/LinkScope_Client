#!/usr/bin/env python3

"""
Credit to: https://github.com/JustAnotherArchivist/snscrape
"""


class TwitterUser:
    name = "Get Tweets by Twitter User"

    category = "Online Identity"

    description = "Get Tweets made by the specified twitter username / handle, or twitter user ID."

    originTypes = {'Social Media Handle', 'Phrase', 'Twitter User', 'VK User'}

    resultTypes = {'Twitter User', 'Tweet', 'Website', 'Ticker', 'Country', 'GeoCoordinates', 'Social Media Handle',
                   'Phrase'}

    parameters = {'Username or User ID': {'description': 'Please specify whether to treat the given inputs as '
                                                         'Twitter usernames or as twitter user IDs.\nA Username, or '
                                                         '"twitter handle" in this case, looks like this: "@example", '
                                                         'whereas a user ID is a long series of numbers.',
                                          'type': 'SingleChoice',
                                          'value': {'Usernames', 'User IDs'},
                                          'default': 'Usernames'},
                  'Max Tweets': {'description': 'Please enter the maximum number of tweets to process, or "0" to '
                                                'return all results. Note that this does not include quoted tweets '
                                                '(i.e. this is how many surface-level tweets to explore).',
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
        import requests
        import pytz
        import snscrape.base
        import snscrape.modules
        import snscrape.version
        from dateutil.parser import parse
        from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QSize
        from PySide6.QtGui import QImage

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
            maxResults = int(parameters['Max Tweets'])
            if maxResults < 0:
                raise ValueError('')
            if maxResults != 0:
                arguments.maxResults = maxResults
        except ValueError:
            return 'Invalid integer specified for "Max Tweets" parameter.'

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

        def parseTweet(tweetItem, parentItemIndex):
            selfItemIndex = len(returnResults)
            returnResults.append([{'Tweet ID': str(tweetItem.id),
                                   'Tweet URL': tweetItem.url,
                                   'Replies': str(tweetItem.replyCount),
                                   'Retweets': str(tweetItem.retweetCount),
                                   'Likes': str(tweetItem.likeCount),
                                   'Quotes': str(tweetItem.quoteCount),
                                   'Coordinates': str(tweetItem.coordinates),
                                   'Place': str(tweetItem.place),
                                   'Entity Type': 'Tweet',
                                   'Date Created': tweetItem.date.isoformat(),
                                   'Notes': str(tweetItem.content)},
                                  {parentItemIndex: {'Resolution': 'Tweet'}}])
            if tweetItem.outlinks:
                for link in set(tweetItem.outlinks):
                    returnResults.append([{'URL': link,
                                           'Entity Type': 'Website'},
                                          {selfItemIndex: {'Resolution': 'External Link in Tweet'}}])
            if tweetItem.cashtags:
                for cashtag in set(tweetItem.cashtags):
                    returnResults.append([{'Ticker ID': cashtag,
                                           'Entity Type': 'Ticker'},
                                          {selfItemIndex: {'Resolution': 'Cashtag in Tweet'}}])
            if tweetItem.hashtags:
                for hashtag in set(tweetItem.hashtags):
                    returnResults.append([{'Phrase': hashtag,
                                           'Entity Type': 'Phrase'},
                                          {selfItemIndex: {'Resolution': 'Hashtag in Tweet'}}])
            if tweetItem.media:
                for mediaItem in tweetItem.media:
                    if hasattr(mediaItem, 'variants'):
                        maxBitrate = 0
                        bestVariant = None
                        for variant in mediaItem.variants:
                            if variant.bitrate and variant.bitrate > maxBitrate:
                                maxBitrate = variant.bitrate
                                bestVariant = variant
                        if bestVariant:
                            videoIndex = len(returnResults)
                            returnResults.append([{'URL': str(bestVariant.url),
                                                   'Entity Type': 'Website'},
                                                  {selfItemIndex: {'Resolution': 'Video in Tweet'}}])
                            returnResults.append([{'URL': str(mediaItem.thumbnailUrl),
                                                   'Entity Type': 'Website'},
                                                  {videoIndex: {'Resolution': 'Video Thumbnail'}}])
                    else:
                        returnResults.append([{'URL': str(mediaItem.fullUrl),
                                               'Entity Type': 'Website'},
                                              {selfItemIndex: {'Resolution': 'Picture in Tweet'}}])
            if tweetItem.coordinates:
                placeName = 'Tweet Location ' + str(tweetItem.id)
                if tweetItem.place:
                    if tweetItem.place.fullName:
                        placeName = str(tweetItem.place.fullName)
                    if tweetItem.place.country:
                        returnResults.append([{'Country Name': str(tweetItem.place.country),
                                               'Entity Type': 'Country'},
                                              {selfItemIndex: {'Resolution': 'Country in Tweet'}}])

                returnResults.append([{'Label': placeName,
                                       'Latitude': str(tweetItem.coordinates.latitude),
                                       'Longitude': str(tweetItem.coordinates.longitude),
                                       'Entity Type': 'GeoCoordinates'},
                                      {selfItemIndex: {'Resolution': 'Coordinates in Tweet'}}])
            if tweetItem.mentionedUsers:
                for userName in tweetItem.mentionedUsers:
                    returnResults.append([{'User Name': userName.username,
                                           'Entity Type': 'Social Media Handle'},
                                          {selfItemIndex: {'Resolution': 'Users mentioned in Tweet'}}])
            if tweetItem.inReplyToTweetId:
                returnResults.append([{'Tweet ID': str(tweetItem.inReplyToTweetId),
                                       'Entity Type': 'Tweet'},
                                      {selfItemIndex: {'Resolution': 'Replying to this Tweet'}}])
            if tweetItem.inReplyToUser:
                try:
                    childTwitterAccIconRequest = requests.get(tweetItem.inReplyToUser.profileImageUrl)
                    childIconByteArray = QByteArray(childTwitterAccIconRequest.content)
                    childIconImageOriginal = QImage().fromData(childIconByteArray)
                    childIconImageScaled = childIconImageOriginal.scaled(QSize(40, 40))
                    childIconByteArrayFin = QByteArray()
                    childImageBuffer = QBuffer(childIconByteArrayFin)
                    childImageBuffer.open(QIODevice.WriteOnly)
                    childIconImageScaled.save(childImageBuffer, "PNG")
                    childImageBuffer.close()
                except Exception:
                    childIconByteArrayFin = None
                returnResults.append([{'Twitter Handle': '@' + tweetItem.inReplyToUser.username,
                                       'User ID': str(tweetItem.inReplyToUser.id),
                                       'User URL': tweetItem.inReplyToUser.url,
                                       'Verified': str(tweetItem.inReplyToUser.verified),
                                       'Display Name': str(tweetItem.inReplyToUser.displayname),
                                       'Location': str(tweetItem.inReplyToUser.location),
                                       'Description': tweetItem.inReplyToUser.description,
                                       'Protected': str(tweetItem.inReplyToUser.protected),
                                       'Followers': str(tweetItem.inReplyToUser.followersCount),
                                       'Following': str(tweetItem.inReplyToUser.friendsCount),
                                       'Statuses': str(tweetItem.inReplyToUser.statusesCount),
                                       'Favourites': str(tweetItem.inReplyToUser.favouritesCount),
                                       'Listed': str(tweetItem.inReplyToUser.listedCount),
                                       'Media': str(tweetItem.inReplyToUser.mediaCount),
                                       'Entity Type': 'Twitter User',
                                       'Icon': childIconByteArrayFin,  # If None -> default twitter user pic
                                       'Date Created': None if tweetItem.inReplyToUser.created is None else
                                       tweetItem.inReplyToUser.created.isoformat()},
                                      {selfItemIndex: {'Resolution': 'Replying to Twitter User'}}])

            if tweetItem.quotedTweet:
                parseTweet(tweetItem.quotedTweet, selfItemIndex)

        for entity in entityJsonList:
            uid = entity['uid']
            if entity['Entity Type'] == 'Phrase':
                primaryField = entity['Phrase']
            elif entity['Entity Type'] == 'Twitter User':
                primaryField = entity['Twitter Handle']
            elif entity['Entity Type'] == 'VK User':
                primaryField = entity['VK Username']
            elif entity['Entity Type'] == 'Social Media Handle':
                primaryField = entity['User Name']
            else:
                continue
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
                                           'Display Name': str(item.user.displayname),
                                           'Location': str(item.user.location),
                                           'Description': item.user.description,
                                           'Protected': str(item.user.protected),
                                           'Followers': str(item.user.followersCount),
                                           'Following': str(item.user.friendsCount),
                                           'Statuses': str(item.user.statusesCount),
                                           'Favourites': str(item.user.favouritesCount),
                                           'Listed': str(item.user.listedCount),
                                           'Media': str(item.user.mediaCount),
                                           'Entity Type': 'Twitter User',
                                           'Icon': iconByteArrayFin,  # If None -> default twitter user pic
                                           'Date Created': item.user.created.isoformat()},
                                          {uid: {'Resolution': 'Twitter User'}}])

                parseTweet(item, childIndex)

                if maxResults and index >= maxResults:
                    break

        return returnResults
