#!/usr/bin/env python3

"""
This class handles the backend stuff for the LinkScope Query Language.
"""


class Query:

    COMPONENTS = ["select-query"]

    def __init__(self):
        super(Query, self).__init__()


class SelectQuery:

    def __init__(self):
        super(SelectQuery, self).__init__()


class LQLQueryBuilder:
    QUERY_PARTS_DICT = {"query": Query,
                        "select-query": SelectQuery}
