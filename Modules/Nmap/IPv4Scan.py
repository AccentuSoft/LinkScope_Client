#!/usr/bin/env python3


class IPv4Scan:
    # A string that is treated as the name of this resolution.
    name = "IPv4 Nmap Scan"

    category = "Network Scanning"

    # A string that describes this resolution.
    description = ""

    originTypes = {'IP Address'}

    resultTypes = {'Phrase'}

    parameters = {'Nmap Vacuum Flags': {'description': 'Select Nmap Vacuum Flags to be used',
                                        'type': 'MultiChoice',
                                        'value': {'-sV', '-O', '-A', '-sL', '-sN', '-Pn', '-PE', '-PP', '-PM', '-n',
                                                  '-R', '-sA', '-sW', '-sM', '-sU', '-sN', '-sF', '-sX', '-sY', '-sZ',
                                                  '-sO'}
                                        },
                  'Nmap Timing Flags': {'description': 'Select Nmap Timing Flags to be used',
                                        'type': 'SingleChoice',
                                        'value': {'-T0', '-T1', '-T2', '-T3', '-T4', '-T5'}
                                        },
                  'Nmap Ports': {'description': 'Select Ports to scan.\n'
                                                'Type ports separated by commas and without spaces, e.g.: 80,443,22\n'
                                                'Type "All" (no quotes) to scan all ports',
                                 'type': 'String',
                                 'value': 'Enter ports to scan here',
                                 'default': 'All'
                                 },
                  # Can Extend Functionality to support the script engine in the future
                  # 'Additional Parameter Commands': {'description': 'Specify any additional commands\n'
                  #                                                 'Type "No Commands" (no quotes)\n '
                  #                                                 'if you do not want to add any additional commands',
                  #                                  'type': 'String',
                  #                                  'value': 'No Commands'
                  #                                  },
                  'Root Privileges': {'description': 'Some Commands require Root Privileges\n'
                                                     'Please make sure you are running LinkScope as a user with sudo '
                                                     'privileges, and provide your password:',
                                      'type': 'String',
                                      'value': ''
                                      }
                  }

    def resolution(self, entityJsonList, parameters):
        import subprocess
        import tempfile
        import xmltodict
        import json
        from ipaddress import ip_address
        from pathlib import Path
        from ast import literal_eval

        returnResults = []
        nmapParams = ["nmap"]
        sudoParams = ["sudo", "-S"]
        passwd = str(parameters['Root Privileges']) + '\n'
        vacuumFlags = parameters['Nmap Vacuum Flags']
        timingFlag = str(parameters['Nmap Timing Flags'])

        for flag in vacuumFlags:
            nmapParams.append(flag)

        nmapParams.append(timingFlag)
        if parameters['Nmap Ports'] != 'All':
            nmapParams.append(f"-p{parameters['Nmap Ports']}")

        for entity in entityJsonList:
            uid = entity['uid']
            primary_field = entity[list(entity)[1]]
            try:
                ip_address(primary_field)
            except ValueError:
                return "The Entity provided isn't a valid IP Address"

            nmapParams.append(primary_field)

            temp_dir = tempfile.TemporaryDirectory()
            xmlPath = Path(temp_dir.name) / 'report.xml'
            nmapParams.append('-oX')
            nmapParams.append(str(xmlPath))

            allParams = sudoParams + nmapParams
            subprocess.Popen(allParams, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE).communicate(input=bytes(passwd, encoding='utf-8'))

            with open(xmlPath, 'r') as f:
                file_content = f.read()  # Read whole file in the file_content string
            jsonData = literal_eval(json.dumps(xmltodict.parse(file_content)).replace('null', 'None'))

            if jsonData['nmaprun'].get('host') is not None:
                if jsonData['nmaprun']['host']['os'].get('osmatch') is not None:
                    osData = jsonData['nmaprun']['host']['os']['osmatch']
                    for osName in osData:
                        if type(osName['osclass']) is list:
                            for osCl in osName['osclass']:
                                returnResults.append([{'OS Name': osName['@name'],
                                                       'Type': osCl['@type'],
                                                       'Vendor': osCl['@vendor'],
                                                       'OS Family': osCl['@osfamily'],
                                                       'CPE': osCl['cpe'],
                                                       'Notes': 'Accuracy: ' + osName['@accuracy'] + ' %',
                                                       'Entity Type': 'Operating System'},
                                                      {uid: {'Resolution': 'OS Found',
                                                             'Notes': ''}}])
                        else:
                            returnResults.append([{'OS Name': osName['@name'],
                                                   'Type': osName['osclass']['@type'],
                                                   'Vendor': osName['osclass']['@vendor'],
                                                   'OS Family': osName['osclass']['@osfamily'],
                                                   'CPE': osName['osclass']['cpe'],
                                                   'Notes': 'Accuracy: ' + osName['@accuracy'] + ' %',
                                                   'Entity Type': 'Operating System'},
                                                  {uid: {'Resolution': 'OS Found',
                                                         'Notes': ''}}])

                if jsonData['nmaprun']['host']['os'].get('osfingerprint') is not None:
                    returnResults.append([{'Phrase': 'Fingerprint: ' + str(jsonData['nmaprun']['host']['os']
                                                                           ['osfingerprint']['@fingerprint'])[
                                                                       0: 15],
                                           'Notes': jsonData['nmaprun']['host']['os']['osfingerprint'][
                                               '@fingerprint'],
                                           'Entity Type': 'Phrase'},
                                          {uid: {'Resolution': 'OS Fingerprint',
                                                 'Notes': ''}}])

                if jsonData['nmaprun']['host']['ports'].get('port') is not None:
                    portData = jsonData['nmaprun']['host']['ports']['port']
                    for port in portData:
                        index_of_child = len(returnResults)
                        returnResults.append([{'Port': primary_field + ':' + port['@portid'] + ':' +
                                                       port['@protocol'],
                                               'State': 'Closed',
                                               'Notes': '',
                                               'Entity Type': 'Port'},
                                              {uid: {'Resolution': 'Port Found',
                                                     'Notes': ''}}])
                        returnResults.append([{'Phrase': port['state']['@state'],
                                               'Entity Type': 'Phrase'},
                                              {index_of_child: {'Resolution': 'Port State',
                                                                'Notes': ''}}])
                        if port['service'].get('@product') is not None:
                            returnResults.append([{'Service Product': port['service'].get('@product'),
                                                   'Service Name': port['service']['@name'],
                                                   'Method': port['service']['@method'],
                                                   'Configuration': port['service']['@conf'],
                                                   'Notes': '',
                                                   'Entity Type': 'Port Service'},
                                                  {index_of_child: {'Resolution': 'Port Service',
                                                                    'Notes': ''}}])
                        if isinstance(port.get('script'), list):
                            for prt in port['script']:
                                if prt.get('elem') is not None and type(prt.get('elem')) is dict:
                                    returnResults.append([{'ID': str(prt['@id']),
                                                           'Output': str(prt['@output']),
                                                           'Key': str(prt['elem']['@key']),
                                                           'Notes': str(prt['elem']['#text']),
                                                           'Entity Type': 'Port Script'},
                                                          {index_of_child: {'Resolution': 'Port Script',
                                                                            'Notes': ''}}])
                                if prt.get('table') is not None and type(prt['table']) is dict:
                                    try:
                                        returnResults.append([{'Key': str(prt['table']['@key']),
                                                               'Notes': str(prt['table']['elem']),
                                                               'Entity Type': 'Port Script'},
                                                              {index_of_child: {'Resolution': 'Port Script',
                                                                                'Notes': ''}}])
                                    except KeyError:
                                        continue
                                if prt.get('table') is not None and type(prt['table']) is list:
                                    for key in prt['table']:
                                        try:
                                            returnResults.append([{'Key': str(key['elem'][0]),
                                                                   'Notes': str(key['elem'][1]),
                                                                   'Entity Type': 'Port Script'},
                                                                  {index_of_child: {'Resolution': 'Port Script',
                                                                                    'Notes': ''}}])
                                        except KeyError:
                                            continue

                                if prt.get('elem') is not None and type(prt.get('elem')) is list:
                                    for ele in prt['elem']:
                                        returnResults.append([{'Key': str(ele['@key']),
                                                               'Output': str(prt['@output']),
                                                               'ID': str(prt['@id']),
                                                               'Notes': ele['#text'],
                                                               'Entity Type': 'Port Script'},
                                                              {index_of_child: {'Resolution': 'Port Script',
                                                                                'Notes': ''}}])

                                if prt.get('elem') is not None and type(prt.get('elem')) is str:
                                    returnResults.append([{'Key': str(prt['elem']),
                                                           'Output': str(prt['@output']),
                                                           'ID': str(prt['@id']),
                                                           'Notes': '',
                                                           'Entity Type': 'Port Script'},
                                                          {index_of_child: {'Resolution': 'Port Script',
                                                                            'Notes': ''}}])

                        elif isinstance(port.get('script'), dict):
                            if port['script'].get('elem') is not None and type(port['script'].get('elem')) is dict:
                                returnResults.append([{'ID': str(port['script']['@id']),
                                                       'Output': str(port['script']['@output']),
                                                       'Key': str(port['script']['elem']['@key']),
                                                       'Notes': str(port['script']['elem']['#text']),
                                                       'Entity Type': 'Port Script'},
                                                      {index_of_child: {'Resolution': 'Port Script',
                                                                        'Notes': ''}}])

                            if port['script'].get('elem') is not None and type(port['script'].get('elem')) is list:
                                for ele in port['script']['elem']:
                                    returnResults.append([{'Key': str(ele['@key']),
                                                           'Output': str(port['script']['@output']),
                                                           'ID': str(port['script']['@id']),
                                                           'Notes': str(ele['#text']),
                                                           'Entity Type': 'Port Script'},
                                                          {index_of_child: {'Resolution': 'Port Script',
                                                                            'Notes': ''}}])

                            if port['script'].get('elem') is not None and type(port['script'].get('elem')) is str:
                                returnResults.append([{'Key': str(port['script']['elem']),
                                                       'Output': str(port['script']['@output']),
                                                       'ID': str(port['script']['@id']),
                                                       'Notes': '',
                                                       'Entity Type': 'Port Script'},
                                                      {index_of_child: {'Resolution': 'Port Script',
                                                                        'Notes': ''}}])

                if jsonData['nmaprun']['host'].get('trace') is not None:
                    trcDataList = jsonData['nmaprun']['host']['trace']['hop']
                    trcData = jsonData['nmaprun']['host']['trace']
                    child = len(returnResults)
                    returnResults.append([{'Port': 'Trace Port: ' + primary_field + ' ' + str(trcData['@port']),
                                           'Notes': '',
                                           'Entity Type': 'Port'},
                                          {uid: {'Resolution': 'Port Found',
                                                 'Notes': ''}}])
                    for hp in trcDataList:
                        returnResults.append([{'IP Address': hp['@ipaddr'],
                                               'TTL': str(hp['@ttl']),
                                               'RTT': str(hp['@rtt']),
                                               'Notes': '',
                                               'Entity Type': 'IP Address'},
                                              {child: {'Resolution': 'Hop ' + str(hp['@ttl']),
                                                       'Notes': ''}}])

                if jsonData['nmaprun'].get('tcpsequence') is not None:
                    tcpseqData = jsonData['nmaprun']['tcpsequence']
                    returnResults.append([{'Index': str(tcpseqData['@index']),
                                           'Difficulty': tcpseqData['@difficulty'],
                                           'Values': tcpseqData['@values'],
                                           'Notes': '',
                                           'Entity Type': 'TCP Sequence'},
                                          {uid: {'Resolution': 'TCP Sequence',
                                                 'Notes': ''}}])
                if jsonData['nmaprun'].get('tcpsequence') is not None:
                    tcpseqData = jsonData['nmaprun']['tcpsequence']
                    returnResults.append([{'Index': str(tcpseqData['@index']),
                                           'Difficulty': tcpseqData['@difficulty'],
                                           'Values': tcpseqData['@values'],
                                           'Notes': '',
                                           'Entity Type': 'TCP Sequence'},
                                          {uid: {'Resolution': 'TCP Sequence',
                                                 'Notes': ''}}])

                if jsonData['nmaprun'].get('ipidsequence') is not None:
                    ipIdSeqData = jsonData['nmaprun']['ipidsequence']
                    returnResults.append([{'Class': ipIdSeqData['@class'],
                                           'Values': ipIdSeqData['@values'],
                                           'Notes': '',
                                           'Entity Type': 'IP ID Sequence'},
                                          {uid: {'Resolution': 'IP ID Sequence',
                                                 'Notes': ''}}])

                if jsonData['nmaprun'].get('tcptssequence') is not None:
                    tcpTsSeqData = jsonData['nmaprun']['tcptssequence']
                    returnResults.append([{'Class': tcpTsSeqData['@class'],
                                           'Values': tcpTsSeqData['@values'],
                                           'Notes': '',
                                           'Entity Type': 'TCP TS Sequence'},
                                          {uid: {'Resolution': 'TCP TS Sequence',
                                                 'Notes': ''}}])

        return returnResults
