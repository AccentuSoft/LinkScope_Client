#!/usr/bin/env python3


class HostnameToIP:
    name = "Hostname To IP"
    description = "Gets the IP associated with the given hostname."
    originTypes = {'Domain', 'Website'}
    resultTypes = {'IP Address', 'IPv6 Address'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import socket

        returnResults = []

        for entity in entityJsonList:
            primaryField = entity[list(entity)[1]]
            urlFeatures = primaryField.find('://')
            if urlFeatures != -1:
                primaryField = primaryField[urlFeatures + 3:]
            try:
                entityResults = socket.getaddrinfo(primaryField, 443, proto=socket.IPPROTO_TCP) + \
                                socket.getaddrinfo(primaryField, 80, proto=socket.IPPROTO_TCP)
            except Exception:
                continue

            for result in entityResults:
                if result[0].value == 2:
                    returnResults.append([{'IP Address': result[4][0],
                                           'Entity Type': 'IP Address'},
                                          {entity['uid']: {'Resolution': 'Hostname To IP',
                                                           'Notes': ''}}])
                elif result[0].value == 10:
                    returnResults.append([{'IPv6 Address': result[4][0],
                                           'Entity Type': 'IPv6 Address'},
                                          {entity['uid']: {'Resolution': 'Hostname To IP',
                                                           'Notes': ''}}])

        return returnResults
