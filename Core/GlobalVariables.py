#!/usr/bin/env python3

import random

non_string_fields = ('Icon', 'Child UIDs')
hidden_fields = ('uid', 'Date Last Edited', 'Child UIDs', 'Canvas Banner', 'Entity Type')
hidden_fields_dockbars = ('uid', 'Child UIDs', 'Canvas Banner', 'Icon')
meta_fields = ('Child UIDs',)
avoid_parsing_fields = ('uid', 'Date Last Edited', 'Child UIDs', 'Icon', 'Canvas Banner')

# Closer to the top means more recent.
user_agents = {'Chrome': {'Windows': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                                      '(KHTML, like Gecko) Chrome/101.0.4951.15 Safari/537.36',),
                          'Linux': ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                    'Chrome/101.0.4951.15 Safari/537.36',)
                          },
               'Firefox': {'Windows': ('Mozilla/5.0 (Windows NT 10.0; rv:100.0) Gecko/20100101 Firefox/98.0',),
                           'Linux': ('Mozilla/5.0 (X11; Linux x86_64; rv:98.0) Gecko/20100101 Firefox/98.0',)
                           },
               'Webkit': {'Windows': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/605.1.15 '
                                      '(KHTML, like Gecko) Version/15.4 Safari/605.1.15',),
                          'Linux': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 '
                                    '(KHTML, like Gecko) Version/15.4 Safari/605.1.15',)
                          }
               }


def getLatestUserAgent(browser: str = None, platform: str = None) -> str:
    if browser is None or browser not in user_agents:
        browser = random.choice(list(user_agents.keys()))
    browserPlatforms = user_agents[browser]
    if platform is None or platform not in browserPlatforms:
        platform = random.choice(list(browserPlatforms.keys()))
    return user_agents[browser][platform][0]


def getUserAgents(browser: str = None, platform: str = None, amount: int = 1) -> tuple:
    if browser is None or browser not in user_agents:
        browser = random.choice(list(user_agents.keys()))
    browserPlatforms = user_agents[browser]
    if platform is None or platform not in browserPlatforms:
        platform = random.choice(list(browserPlatforms.keys()))
    return user_agents[browser][platform][:amount]
