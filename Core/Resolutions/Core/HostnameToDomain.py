#!/usr/bin/env python3


class HostnameToDomain:
    name = "Hostname to Domain"
    description = "Find the domain of any given hostname."
    originTypes = {'Domain', 'Website'}
    resultTypes = {'Domain'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        from tldextract import extract

        return_result = []
        for entity in entityJsonList:
            uid = entity['uid']
            primary_field = entity[list(entity)[1]].strip()
            tsd, td, tsu = extract(primary_field)
            domain = td + '.' + tsu
            if domain == primary_field:
                continue
            return_result.append([{'Domain Name': domain,
                                   'Entity Type': 'Domain'},
                                  {uid: {'Resolution': 'Domain to Hostname', 'Notes': ''}}])
        return return_result
