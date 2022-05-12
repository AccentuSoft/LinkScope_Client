#!/usr/bin/env python3


class WikiLeaksSearch:
    name = "WikiLeaks Search"
    category = "Leaked Data"
    description = "Find mentions of a Phrase or Domain in WikiLeaks."
    originTypes = {'Phrase', 'Domain'}
    resultTypes = {'Website'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import requests
        import re
        from bs4 import BeautifulSoup

        cleanTagsRegex = re.compile(r'<.*?>')

        baseURLPart1 = "https://search.wikileaks.org/advanced?query="
        baseURLPart2 = "&released_date_start=&new_search=True&released_date_end=&any_of=" \
                       "&include_external_sources=True&exact_phrase="
        baseURLPart3 = "&page="
        baseURLPart4 = "&exclude_words=&order_by=newest_document_date&document_date_end=&document_date_start="

        returnResults = []

        for entity in entityJsonList:
            uid = entity['uid']
            if entity['Entity Type'] == 'Phrase':
                requestUrlBase = baseURLPart1 + entity['Phrase'] + baseURLPart2 + baseURLPart3
            elif entity['Entity Type'] == 'Domain':
                requestUrlBase = baseURLPart1 + baseURLPart2 + entity['Domain Name'] + baseURLPart3
            else:
                continue

            pageCount = 1
            while True:
                requestResult = requests.get(requestUrlBase + str(pageCount) + baseURLPart4)
                resultSoup = BeautifulSoup(requestResult.content, 'lxml')
                resultsList = resultSoup.find_all("div", {"class": "result"})
                if len(resultsList) == 0:
                    break
                for result in resultsList:
                    try:
                        excerpt = result.find_all('div', {"class": "excerpt"})[0].text
                        excerpt = excerpt.replace("\n", "")
                        excerpt = excerpt.replace("\t", " ")
                        excerpt = re.sub(cleanTagsRegex, '', excerpt)
                    except IndexError:
                        excerpt = ""
                    try:
                        referenceURL = result.find_all('a')[0]['href']
                        returnResults.append([{'URL': referenceURL,
                                               'Entity Type': 'Website',
                                               'Notes': excerpt},
                                              {uid: {'Resolution': 'WikiLeaks Result',
                                                     'Notes': ''}}])
                    except (IndexError, KeyError):
                        continue
                pageCount += 1

        return returnResults
