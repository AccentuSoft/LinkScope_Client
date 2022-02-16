#!/usr/bin/env python3


class TwitterSearchByKeyWord:
    name = "Get Tweets by Keyword"

    description = """
    Returns Tweets per ID.
    """

    originTypes = {'Phrase'}

    resultTypes = {'Phrase'}

    parameters = {'Max Results': {'description': 'Please enter the maximum number of results to return.',
                                  'type': 'String',
                                  'default': '5'},
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
        try:
            linkNumbers = int(parameters['Max Results'])
        except ValueError:
            return "Invalid integer provided in 'Max Results' parameter"
        if linkNumbers <= 0:
            return []
        access_token = parameters['Access Token'].strip()
        access_token_secret = parameters['Secret'].strip()
        consumer_key = parameters['Consumer API Key'].strip()
        consumer_secret = parameters['Consumer Secret Key'].strip()

        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)

        api = tweepy.API(auth)

        for entity in entityJsonList:
            uid = entity['uid']
            phrase = entity['Phrase']

            cursor = tweepy.Cursor(api.user_timeline, q=phrase, tweeet_mode='extended').items(linkNumbers)

            try:
                for tweet in cursor:
                    index_of_child = len(returnResults)
                    returnResults.append([{'Phrase': tweet.text[0: 15] + ' Full Tweet in Notes',
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
