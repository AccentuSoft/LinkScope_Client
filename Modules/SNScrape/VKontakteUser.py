#!/usr/bin/env python3

"""
Credit to: https://github.com/JustAnotherArchivist/snscrape
"""


class VKontakteUser:
    name = "Get Posts by VKontakte User"

    description = "Get Posts made by the specified VKontakte username."

    originTypes = {'Social Media Handle', 'Phrase', 'Twitter User', 'VK User'}

    resultTypes = {'Website', 'VK Post', 'VK User'}

    parameters = {'Max Results': {'description': 'Please enter the maximum number of results to return, or "0" to '
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
        import pytz
        import snscrape.base
        import snscrape.modules
        import snscrape.version
        from dateutil.parser import parse

        classes = snscrape.base.Scraper.__subclasses__()
        scrapers = {}
        for cls in classes:
            if cls.name is not None:
                scrapers[cls.name] = cls
            classes.extend(cls.__subclasses__())

        arguments = argparse.Namespace(citation=None, verbosity=0, dumpLocals=False, retries=3, maxResults=None,
                                       format=None, jsonl=True, withEntity=True, since=None, progress=False,
                                       scraper='vkontakte-user', isUserId=False, username='')

        try:
            maxResults = int(parameters['Max Results'])
            if maxResults < 0:
                raise ValueError('')
            if maxResults != 0:
                arguments.maxResults = maxResults + 1  # Need to add 1 to account for User entity.
        except ValueError:
            return 'Invalid integer specified for "Max Results" parameter.'

        if parameters['Start Date'] != 'NONE':
            try:
                sinceDate = parse(parameters['Start Date'])
                if sinceDate.tzinfo is None:
                    sinceDate = sinceDate.replace(tzinfo=pytz.UTC)
                arguments.since = sinceDate.date()  # Time information is not available
            except ValueError:
                return 'Invalid date specified for "Start Date" parameter.'

        returnResults = []

        def parsePost(postItem, parentItemIndex):
            selfItemIndex = len(returnResults)
            returnResults.append([{'VK Post URL': postItem.url,
                                   'Entity Type': 'VK Post',
                                   'Date Created': postItem.date.isoformat(),
                                   'Notes': str(postItem.content)},
                                  {parentItemIndex: {'Resolution': 'VK Post'}}])
            if postItem.outlinks:
                for outlink in set(postItem.outlinks):
                    returnResults.append([{'URL': outlink,
                                           'Entity Type': 'Website'},
                                          {selfItemIndex: {'Resolution': 'External Link in Post'}}])
            if postItem.photos:
                for photo in postItem.photos:
                    variantURLs = []
                    for variant in photo.variants:
                        variantURLs.append(variant.url)
                    returnResults.append([{'URL': photo.url,
                                           'Entity Type': 'Website',
                                           'Notes': "Variants:\n" + "\n".join(variantURLs)},
                                          {selfItemIndex: {'Resolution': 'Photo in Post'}}])
            if postItem.video:
                # videoIndex = len(returnResults)
                returnResults.append([{'URL': postItem.video.url,
                                       'Entity Type': 'Website'},
                                      {selfItemIndex: {'Resolution': 'Video in Post'}}])
                # Does not always contain valid urls for some reason.
                # returnResults.append([{'URL': postItem.video.thumbUrl,
                #                       'Entity Type': 'Website'},
                #                      {videoIndex: {'Resolution': 'Video Thumbnail'}}])
            if postItem.quotedPost:
                parsePost(postItem.quotedPost, selfItemIndex)

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
            # Strip the '@' if it exists.
            if primaryField.startswith('@'):
                primaryField = primaryField[1:]
            arguments.username = primaryField

            scraper = scrapers['vkontakte-user'].cli_from_args(arguments)
            item = scraper.entity

            childIndex = len(returnResults)
            returnResults.append([{'VK Username': item.username,
                                   'Name': str(item.name),
                                   'Verified': str(item.verified),
                                   'Description': str(item.description),
                                   'Followers': str(item.followers),
                                   'Following': str(item.following),
                                   'Posts': str(item.posts),
                                   'Photos': str(item.photos),
                                   'Entity Type': 'VK User'},
                                  {uid: {'Resolution': 'Twitter User'}}])

            for index, item in enumerate(scraper.get_items(), start=1):
                if arguments.since is not None and item.date < arguments.since:
                    break
                parsePost(item, childIndex)
                if maxResults and index >= maxResults:
                    break

        return returnResults
