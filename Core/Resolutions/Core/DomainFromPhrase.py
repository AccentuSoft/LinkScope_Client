#!/usr/bin/env python3


class DomainFromPhrase:
    name = "Domain From Phrase"
    category = "String Operations"
    description = "Extract domain-like objects from a phrase."
    originTypes = {'Phrase'}
    resultTypes = {'Domain'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import re
        import tldextract

        domainRegex = re.compile(
            r'^(([a-zA-Z]{1})|([a-zA-Z]{1}[a-zA-Z]{1})|'
            r'([a-zA-Z]{1}[0-9]{1})|([0-9]{1}[a-zA-Z]{1})|'
            r'([a-zA-Z0-9][-_.a-zA-Z0-9]{0,61}[a-zA-Z0-9]))\.'
            r'([a-zA-Z]{2,13}|[a-zA-Z0-9-]{2,30}.[a-zA-Z]{2,3})$'
        )
        wordChar = re.compile(r'\w')

        returnResults = []

        for entity in entityJsonList:
            primaryField = entity['Phrase'].lower()
            for entityChunk in primaryField.split():
                while wordChar.match(entityChunk[-1]) is None:
                    entityChunk = entityChunk[:-1]
                if domainRegex.match(entityChunk):
                    try:
                        tldObject = tldextract.extract(entityChunk)
                        if tldObject.suffix != '':
                            returnResults.append([{'Domain Name': entityChunk,
                                                   'Entity Type': 'Domain'},
                                                  {entity['uid']: {'Resolution': 'Phrase To Domain',
                                                                   'Notes': ''}}])
                    except Exception:
                        pass

        return returnResults
