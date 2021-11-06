#!/usr/bin/env python3


class Reddit:
    name = "Reddit Comments and Submissions Lookup"
    description = "Search Reddit for Phrases or Persons ('Authors') sorted by most recent."
    originTypes = {'Phrase', 'Person'}
    resultTypes = {'Phrase'}
    parameters = {'Content to search': {'description': "Select the type of content to search:\n The Comments endpoint "
                                                       "will search for users' comments.\n The Submission will "
                                                       "look for posts by users in subreddits.",
                                        'type': 'MultiChoice',
                                        'value': {'comments', 'submission'}},
                  'Number of results': {'description': 'Creating a lot of nodes could slow down the software. Please '
                                                       'be mindful of the value you enter.',
                                        'type': 'String',
                                        'value': 'Enter the number of results you want returned',
                                        'default': '10'}}

    def resolution(self, entityJsonList, parameters):
        import requests
        import hashlib
        from binascii import hexlify
        from requests_futures.sessions import FuturesSession
        from concurrent.futures import as_completed

        return_result = []
        uidList = []
        futures = []

        endpoint = parameters['Content to search']

        try:
            size = int(parameters['Number of results'])
        except ValueError:
            return "The value for parameter 'Max Results' is not a valid integer."

        # Endpoints
        comments_endpoint = "https://api.pushshift.io/reddit/search/comment"
        submission_endpoint = "https://api.pushshift.io/reddit/search/submission"

        with FuturesSession(max_workers=15) as session:
            for entity in entityJsonList:
                primary_field = entity[list(entity)[1]].strip()
                if 'submission' in endpoint:
                    uidList.append(entity['uid'])
                    crafted_url = f"{submission_endpoint}/?q=\"{primary_field}\"&sort=desc&size={size}"
                    futures.append(session.get(crafted_url))
                if 'comments' in endpoint:
                    uidList.append(entity['uid'])
                    crafted_url = f"{comments_endpoint}/?q=\"{primary_field}\"&sort=desc&size={size}"
                    futures.append(session.get(crafted_url))
        for future in as_completed(futures):
            uid = uidList[futures.index(future)]
            try:
                response = future.result().json()
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"
            # print(response)
            for value in response['data']:
                index_of_child = len(return_result)
                return_result.append([{'Subreddit': value['subreddit'],
                                       'Entity Type': 'Reddit Subreddit'},
                                      {uid: {'Resolution': 'Reddit Subreddit', 'Notes': ''}}])
                if submission_endpoint in future.result().url:
                    return_result.append([{'Full Name': value['author'],
                                           'Entity Type': 'Person'},
                                          {index_of_child: {'Resolution': str(value['full_link']), 'Notes': ''}}])
                elif comments_endpoint in future.result().url:
                    index_of_child_of_child = len(return_result)
                    return_result.append([{'Full Name': value['author'],
                                           'Entity Type': 'Person'},
                                          {index_of_child: {'Resolution': f"https://reddit.com{value['permalink']}",
                                                            'Notes': ''}}])
                    comment = hashlib.md5(value['body'].encode())
                    comment = hexlify(comment.digest()).decode()
                    return_result.append([{'Comment': comment,
                                           'Notes': value['body'],
                                           'Entity Type': 'Reddit Comment'},
                                          {index_of_child_of_child: {'Resolution': 'Reddit Comment Hashed',
                                                                     'Notes': ''}}])
        return return_result
