#!/usr/bin/env python3


class TwitterSearchByID:
    name = "Get Tweets by Twitter Handle"

    description = """
    Returns Tweets per ID.
    """

    originTypes = {'Social Media Handle'}

    resultTypes = {'Phrase'}

    parameters = {'Max Results': {'description': 'Please enter the maximum number of results to return. '
                                                 'Enter "0" (no quotes) to return all available results.',
                                  'type': 'String',
                                  'default': '0'},
                  'Access Token': {
                      'description': 'Enter your API Key',
                      'type': 'String',
                      'value': ''},
                  'Secret': {
                      'description': 'Enter your Secret Key.',
                      'type': 'String',
                      'value': ''},
                  'Consumer API Key': {
                      'description': 'Enter your API Key',
                      'type': 'String',
                      'value': ''},
                  'Consumer Secret Key': {
                      'description': 'Enter your Secret Key.',
                      'type': 'String',
                      'value': ''},
                  }

    def resolution(self, entityJsonList, parameters):
        import tweepy

        returnResults = []
        linkNumbers = int(parameters['Max Results'])
        access_token = parameters['Access Token'].strip()
        access_token_secret = parameters['Secret'].strip()
        consumer_key = parameters['Consumer API Key'].strip()
        consumer_secret = parameters['Consumer Secret Key'].strip()

        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)

        api = tweepy.API(auth)

        for entity in entityJsonList:
            uid = entity['uid']
            twitter_id = entity['Twitter ID']
            if linkNumbers == 0:
                linkNumbers = 9999999999

            cursor = tweepy.Cursor(api.user_timeline, id=twitter_id, tweeet_mode='extended').items(linkNumbers)

            try:
                for tweet in cursor:
                    index_of_child = len(returnResults)
                    returnResults.append([{'Phrase':
                                               tweet.text[0: 15] + ' Full Tweet in Notes',
                                           'Notes': tweet.text,
                                           # 'Date Created': tweet.created_at,
                                           'Entity Type': 'Phrase'},
                                          {uid: {'Resolution': 'Tweet', 'Notes': ''}}])
                    returnResults.append([{'Phrase': 'Re-Tweet Count: ' + str(tweet.retweet_count),
                                           'Entity Type': 'Phrase'},
                                          {index_of_child: {'Resolution': 'Re-Tweet Count:', 'Notes': ''}}])
                    returnResults.append([{'Phrase': 'Favorite Count: ' + str(tweet.favorite_count),
                                           'Entity Type': 'Phrase'},
                                          {index_of_child: {'Resolution': 'Favorite Count', 'Notes': ''}}])
            except tweepy.TweepError:
                return 'Invalid API Keys'

        return returnResults
