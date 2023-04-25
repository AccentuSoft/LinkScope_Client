#!/usr/bin/env python3

"""
Credit:
https://github.com/Mennaruuk/twayback
"""


class Twayback:
    name = "Get Deleted Tweets"
    category = "Online Identity"
    description = "Get any deleted tweets belonging to the twitter user specified."
    originTypes = {'Social Media Handle', 'Phrase', 'Twitter User'}
    resultTypes = {'Website'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import requests
        import contextlib
        import bs4
        import re
        from requests_futures.sessions import FuturesSession
        from concurrent.futures import as_completed
        from time import sleep

        returnResults = []

        for entity in entityJsonList:
            uid = entity['uid']
            account_name = entity[list(entity)[1]]
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; DuckDuckBot-Https/1.1; https://duckduckgo.com/duckduckbot)'}
            futures = []

            wayback_cdx_url = f"https://web.archive.org/cdx/search/cdx?url=twitter.com/{account_name}/status" \
                              f"&matchType=prefix&filter=statuscode:200&mimetype:text/html&from=&to="
            cdx_page_text = requests.get(wayback_cdx_url).text

            if len(re.findall(r'Blocked', cdx_page_text)) != 0:
                return f"Sorry, no deleted Tweets can be retrieved for {account_name}.\n" \
                       f"This is because the Wayback Machine excludes Tweets for this handle."

            # Capitalization does not matter for twitter links. Url parameters after '?' do not matter either.
            tweet_id_and_url_dict = {line.split()[2].lower().split('?')[0]: line.split()[1] for line in
                                     cdx_page_text.splitlines()}

            with FuturesSession(max_workers=10) as session:
                futures.extend(
                    session.get(
                        twitter_url,
                        headers=headers,
                        timeout=30,
                        allow_redirects=False,
                    )
                    for twitter_url in tweet_id_and_url_dict
                )
            missing_tweets = {}

            for future in as_completed(futures):
                # Cannot display progress or log stuff here, as this is done in other threads.
                page_response = future.result()
                if page_response.status_code == 404:
                    split_once = page_response.url.split('/status/')[-1]
                    split_fin = re.split(r'\D', split_once)[0]
                    missing_tweets[page_response.url] = split_fin

            wayback_url_list = {
                number: f"https://web.archive.org/web/{number}/{url}"
                for url, number in missing_tweets.items()
            }
            deleted_tweets_futures_retry = []

            futures_list = []
            regex = re.compile('.*TweetTextSize TweetTextSize--jumbo.*')

            with FuturesSession(max_workers=10) as session:
                futures_list.extend(
                    session.get(url, headers=headers, timeout=30)
                    for url in wayback_url_list.values()
                )
            for future in as_completed(futures_list):
                result = None
                try:
                    result = future.result()
                    tweet = bs4.BeautifulSoup(result.content, "lxml").find("p", {"class": regex}).getText()
                    returnResults.append([{'URL': result.url,
                                           'Entity Type': 'Website',
                                           'Notes': tweet},
                                          {uid: {'Resolution': 'Deleted Tweet'}}])
                except AttributeError:
                    pass
                except ConnectionError:
                    if result is not None:
                        deleted_tweets_futures_retry.append(result.url)

            # Second try, if things go wrong.
            if deleted_tweets_futures_retry:
                sleep(10)
                futures_list = []
                with FuturesSession(max_workers=10) as session:
                    futures_list.extend(session.get(url) for url in deleted_tweets_futures_retry)
                for future in as_completed(futures_list):
                    with contextlib.suppress(AttributeError, ConnectionError):
                        result = future.result()
                        tweet = bs4.BeautifulSoup(result.content, "lxml").find("p", {"class": regex}).getText()
                        returnResults.append([{'URL': result.url,
                                               'Entity Type': 'Website',
                                               'Notes': tweet},
                                              {uid: {'Resolution': 'Deleted Tweet'}}])
        return returnResults
