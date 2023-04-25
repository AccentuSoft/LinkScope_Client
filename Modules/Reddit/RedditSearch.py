#!/usr/bin/env python3


class RedditSearch:
    name = "Reddit Comments and Submissions Lookup"
    category = "Reddit"
    description = "Search Reddit for Phrases or Persons ('Authors') sorted by most recent."
    originTypes = {'Phrase', 'Person'}
    resultTypes = {'Reddit Comment', 'Social Media Handle', 'Reddit Subreddit'}
    parameters = {'Content to search': {'description': "Select the type of content to search:\n The Comments endpoint "
                                                       "will search for users' comments.\n The Submission will "
                                                       "look for posts by users in subreddits.",
                                        'type': 'MultiChoice',
                                        'value': {'comments', 'submission'}},
                  'Number of results': {'description': 'Enter the maximum number of results you want returned. '
                                                       'Creating a lot of nodes could slow down the software. Please '
                                                       'be mindful of the value you enter.',
                                        'type': 'String',
                                        'value': '',
                                        'default': '10'}}

    def resolution(self, entityJsonList, parameters):
        import requests
        import hashlib
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
            for value in response['data']:
                index_of_child = len(return_result)
                return_result.append([{'Subreddit': value['subreddit'],
                                       'Entity Type': 'Reddit Subreddit'},
                                      {uid: {'Resolution': 'Reddit Subreddit', 'Notes': ''}}])
                resolution_name = value.get('permalink', None)
                if resolution_name is None:
                    resolution_name = 'Link ID: ' + value.get('link_id', 'N/A')
                else:
                    resolution_name = f'https://reddit.com{resolution_name}'

                if submission_endpoint in future.result().url:
                    return_result.append([{'User Name': value['author'],
                                           'Entity Type': 'Social Media Handle'},
                                          {index_of_child: {'Resolution': resolution_name, 'Notes': ''}}])
                elif comments_endpoint in future.result().url:
                    index_of_child_of_child = len(return_result)
                    return_result.append([{'User Name': value['author'],
                                           'Entity Type': 'Social Media Handle'},
                                          {index_of_child: {'Resolution': resolution_name,
                                                            'Notes': ''}}])

                    comment_resolution = 'Reddit Comment Hash'
                    comment = hashlib.md5(value.get('body', 'N/A').encode()).hexdigest()  # nosec
                    return_result.append([{'Comment': comment,
                                           'Notes': value.get('body', 'N/A'),
                                           'Entity Type': 'Reddit Comment'},
                                          {index_of_child_of_child: {'Resolution': comment_resolution,
                                                                     'Notes': ''}}])
        return return_result
