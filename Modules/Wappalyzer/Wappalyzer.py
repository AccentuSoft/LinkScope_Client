#!/usr/bin/env python3


class Wappalyzer:
    name = "Wappalyzer Website Analysis"
    description = "Find information about what technologies a website is using"
    originTypes = {'Website', 'Domain'}
    resultTypes = {'Website Infrastructure'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        from Wappalyzer import Wappalyzer, WebPage

        return_result = []
        for entity in entityJsonList:
            uid = entity['uid']
            primary_field = entity[list(entity)[1]].strip()
            if not primary_field.startswith('http://') and not primary_field.startswith('https://'):
                primary_field = 'http://' + primary_field
            webpage = WebPage.new_from_url(primary_field)
            wappalyzer = Wappalyzer.latest()
            for cms in wappalyzer.analyze(webpage):
                return_result.append([{'Infrastructure': cms,
                                       'Entity Type': 'Website Infrastructure'},
                                      {uid: {'Resolution': 'Wappalyzer Scan', 'Notes': ''}}])
            return return_result
