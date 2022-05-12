#!/usr/bin/env python3


class HaveIBeenPwned:  # TODO https://haveibeenpwned.com/API/v3

    name = "HIBP Database Lookup"
    category = "Leaked Data"
    description = "Find ."  # TODO
    originTypes = {'Phrase', 'Person', 'Social Media Handle'}
    resultTypes = {'Website'}
    parameters = {}  # TODO

    def resolution(self, entityJsonList, parameters):
        import requests
        pass
