#!/usr/bin/env python3


class IPToHostname:
    name = "IP To Hostname"
    category = "Network Infrastructure"
    description = "Gets the Fully Qualified Domain Name associated with the given IPv4 / IPv6 address."
    originTypes = {'IPv6 Address', 'IP Address'}
    resultTypes = {'Domain'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import socket

        returnResults = []

        for entity in entityJsonList:
            primaryField = entity[list(entity)[1]]
            try:
                fqdn = socket.getfqdn(primaryField)
            except Exception:
                continue

            if fqdn != primaryField:
                returnResults.append([{'Domain Name': fqdn,
                                       'Entity Type': 'Domain'},
                                      {entity['uid']: {'Resolution': 'Fully Qualified Domain Name',
                                                       'Notes': ''}}])

        return returnResults
