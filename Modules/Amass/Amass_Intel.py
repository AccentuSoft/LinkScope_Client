#!/usr/bin/env python3
# User needs to be in docker group or have root privileges

class Amass_Intel:
    name = "Amass Intel Scan"
    description = "Find information about a particular domain"
    originTypes = {'Domain', 'IP Address', 'Autonomous System', 'Phrase', 'Company', 'Organization'}
    resultTypes = {'Domain', 'IP Address', 'Autonomous System', 'Phrase', 'Company', 'Organization'}
    parameters = {'VirusTotal': {'description': 'Enter your api key under your profile after'
                                                ' signing up on https://virustotal.com.',
                                 'type': 'String',
                                 'value': 'None'},
                  'AlienVault': {'description': 'Enter your api key under your profile after'
                                                ' signing up on https://otx.alienvault.com.',
                                 'type': 'String',
                                 'value': 'None'},
                  'BinaryEdge': {'description': 'Enter your api key under your profile after'
                                                ' signing up on https://app.binaryedge.com.',
                                 'type': 'String',
                                 'value': 'None'},
                  'C99': {'description': 'Enter your api key under your profile after'
                                         ' signing up on https://c99.nl.',
                          'type': 'String',
                          'value': 'None'},
                  'Censys': {'description': 'Enter your api key under your profile after'
                                            ' signing up on https://censys.io.',
                             'type': 'String',
                             'value': 'None'},
                  'Chaos': {'description': 'Enter your api key under your profile after'
                                           ' signing up on https://chaos.projectdiscovery.io.',
                            'type': 'String',
                            'value': 'None'},
                  'Cloudflare': {'description': 'Enter your api key under your profile after'
                                                ' signing up on https://cloudflare.com.',
                                 'type': 'String',
                                 'value': 'None'},
                  'DNSDB': {'description': 'Enter your api key under your profile after'
                                           ' signing up on https://dnsdb.info.',
                            'type': 'String',
                            'value': 'None'},
                  'GitHub': {'description': 'Enter your api key under your profile after'
                                            ' signing up on https://github.com.',
                             'type': 'String',
                             'value': 'None'},
                  'Hunter': {'description': 'Enter your api key under your profile after'
                                            ' signing up on https://hunter.io.',
                             'type': 'String',
                             'value': 'None'},
                  'IPinfo': {'description': 'Enter your api key under your profile after'
                                            ' signing up on https://ipinfo.io.',
                             'type': 'String',
                             'value': 'None'},
                  'NetworksDB': {'description': 'Enter your api key under your profile after'
                                                ' signing up on https://networksdb.io.',
                                 'type': 'String',
                                 'value': 'None'},
                  'PassiveTotal': {'description': 'Enter your api key under your profile after'
                                                  ' signing up on https://passivetotal.com .',
                                   'type': 'String',
                                   'value': 'None'},
                  'ReconDev': {'description': 'Enter your api key under your profile after'
                                              ' signing up on https://recon.dev.',
                               'type': 'String',
                               'value': 'None'},
                  'SecurityTrails': {'description': 'Enter your api key under your profile after'
                                                    ' signing up on https://securitytrails.com.',
                                     'type': 'String',
                                     'value': 'None'},
                  'Shodan': {'description': 'Enter your api key under your profile after'
                                            ' signing up on https://shodan.io.',
                             'type': 'String',
                             'value': 'None'},
                  'Spyse': {'description': 'Enter your api key under your profile after'
                                           ' signing up on https://spyse.com.',
                            'type': 'String',
                            'value': 'None'},
                  'ThreatBook': {'description': 'Enter your api key under your profile after'
                                                ' signing up on https://threatbook.cn.',
                                 'type': 'String',
                                 'value': 'None'},
                  'Umbrella': {'description': 'Enter your api key under your profile after'
                                              ' signing up on https://umbrella.cisco.com.',
                               'type': 'String',
                               'value': 'None'},
                  'URLScan': {'description': 'Enter your api key under your profile after'
                                             ' signing up on https://urlscan.io.',
                              'type': 'String',
                              'value': 'None'},
                  'WhoisXMLAPI': {'description': 'Enter your api key under your profile after'
                                                 ' signing up on https://whoisxmlapi.com.',
                                  'type': 'String',
                                  'value': 'None'},
                  'ZETAlytics': {'description': 'Enter your api key under your profile after'
                                                ' signing up on https://zetalytics.com.',
                                 'type': 'String',
                                 'value': 'None'},
                  'ZoomEye': {'description': 'Please Enter the Username and password with a space '
                                             'in between',
                              'type': 'String',
                              'value': 'None'},
                  'FacebookCT': {'description': 'Please Enter the api key and secret with a space '
                                                'in between. Obtain them at https://developer.facebook.com',
                                 'type': 'String',
                                 'value': 'None'},
                  'Twitter': {'description': 'Please Enter the api key and secret with a space '
                                             'in between. Obtain them at https://developer.twitter.com',
                              'type': 'String',
                              'value': 'None'},
                  'ReconDev.free': {
                      'description': 'Please Enter the api key under your"\
                       "profile after signing up on https://recon.dev',
                      'type': 'String',
                      'value': 'None'},
                  'ReconDev.paid': {
                      'description': 'Please Enter the api key under your profile"\
                       "after signing up on https://recon.dev',
                      'type': 'String',
                      'value': 'None'}}

    def resolution(self, entityJsonList, parameters):
        from pathlib import Path
        import json
        from ipaddress import ip_address, IPv4Address, IPv6Address
        import docker
        import tempfile
        from docker.errors import APIError

        return_result = []
        client = docker.from_env()
        # Generate Config as a temporary file:
        for entity in entityJsonList:
            primary_field = entity[list(entity)[1]].strip()
            try:
                with tempfile.TemporaryDirectory() as tempDir:
                    tempPath = Path(tempDir).absolute()
                    config = tempfile.NamedTemporaryFile(mode='w+t', prefix='Amass',
                                                         suffix='Config',
                                                         dir=tempPath)
                    config.write("share = true\n")
                    config.write("[scope]\n")
                    config.write("port = 80\n")
                    config.write("port = 443\n")
                    config.write("[data_sources]\n")
                    config.write("minimum_ttl = 1440\n")
                    for parameter in parameters:
                        if parameters[f'{parameter}'] != 'None':
                            field1 = f"[data_sources.{parameter}]"
                            field2 = f"[data_sources.{parameter}.Credentials]"
                            if parameter == "ZoomEye":
                                username, password = parameters[parameter].split(' ', 1)
                                config.write(f"{field1}\n")
                                config.write(f"{field2}\n")
                                config.write(f"username = {username}\n")
                                config.write(f"password = {password}\n")
                            elif parameter == "FacebookCT":
                                field3, secret = parameters[parameter].split(' ', 1)
                                config.write(f"{field1}\n")
                                config.write(f"[data_sources.{parameter}.app1\n")
                                config.write(f"apikey = \"{field3}\"\n")
                                config.write(f"secret = {secret}\n")
                            elif parameter == "Twitter":
                                field3, secret = parameters[parameter].split(' ', 1)
                                config.write(f"{field1}\n")
                                config.write(f"[data_sources.{parameter}.account1\n")
                                config.write(f"apikey = \"{field3}\"\n")
                                config.write(f"secret = {secret}\n")
                            elif parameter == "ReconDev.paid":
                                field3 = parameters[f'{parameter}']
                                config.write(f"{field1}\n")
                                config.write(f"[data_sources.{parameter}.paid\n")
                                config.write(f"apikey = \"{field3}\"\n")
                            elif parameter == "ReconDev.free":
                                field3 = parameters[f'{parameter}']
                                config.write(f"{field1}\n")
                                config.write(f"[data_sources.{parameter}.free\n")
                                config.write(f"apikey = \"{field3}\"\n")
                            else:
                                field3 = parameters[f'{parameter}']
                                config.write(f"{field1}\n")
                                config.write(f"{field2}\n")
                                config.write(f"apikey = \"{field3}\"\n")
                            path_to_config = config.name
                            path_to_config = path_to_config.replace(str(tempPath), "")
                            config.seek(0)
                            # print(config.read())
                            # print(path_to_config)
                            # print(entity['Entity Type'])
                            if entity['Entity Type'] == "Domain":
                                container = client.containers.run("caffix/amass:latest",
                                                                  f"intel -src -d {primary_field} -config /.config/amass"
                                                                  f"{path_to_config}",
                                                                  volumes={
                                                                      str(tempPath): {'bind': '/.config/amass',
                                                                                      'mode': 'rw'}},
                                                                  remove=True)
                            elif entity['Entity Type'] == "Organization" or entity['Entity Type'] == "Phrase" or entity[
                                    'Entity Type'] == "Company":
                                container = client.containers.run("caffix/amass:latest",
                                                                  f"intel -src -org {primary_field} -whois -config "
                                                                  f"/.config/amass{path_to_config}",
                                                                  volumes={
                                                                      str(tempPath): {'bind': '/.config/amass',
                                                                                      'mode': 'rw'}},
                                                                  remove=True)
                            elif entity['Entity Type'] == "IP Address":
                                try:
                                    ip_address(primary_field)
                                except ValueError:
                                    return "The Entity Provided isn't a valid IP Address"
                                container = client.containers.run("caffix/amass:latest",
                                                                  f"intel -src -addr {primary_field} -whois -config "
                                                                  f"/.config/amass{path_to_config}",
                                                                  volumes={
                                                                      str(tempPath): {'bind': '/.config/amass',
                                                                                      'mode': 'rw'}},
                                                                  remove=True)
                            elif entity['Entity Type'] == "Autonomous System":
                                container = client.containers.run("caffix/amass:latest",
                                                                  f"intel -src -asn {entity[list(entity)[2]].strip()}   "
                                                                  f" -whois -config /.config/amass{path_to_config}",
                                                                  volumes={
                                                                      str(tempPath): {'bind': '/.config/amass',
                                                                                      'mode': 'rw'}},
                                                                  remove=True)
                        else:
                            if entity['Entity Type'] == "Domain":
                                container = client.containers.run("caffix/amass:latest",
                                                                  f"intel -src -d {primary_field}",
                                                                  volumes={
                                                                      str(tempPath): {'bind': '/.config/amass',
                                                                                      'mode': 'rw'}},
                                                                  remove=True)
                            elif entity['Entity Type'] == "Organization" or entity['Entity Type'] == "Phrase" or entity[
                                    'Entity Type'] == "Company":
                                container = client.containers.run("caffix/amass:latest",
                                                                  f"intel -src -org {primary_field} -whois",
                                                                  volumes={
                                                                      str(tempPath): {'bind': '/.config/amass',
                                                                                      'mode': 'rw'}},
                                                                  remove=True)
                            elif entity['Entity Type'] == "IP Address":
                                try:
                                    ip_address(primary_field)
                                except ValueError:
                                    return "The Entity Provided isn't a valid IP Address"
                                container = client.containers.run("caffix/amass:latest",
                                                                  f"intel -src -addr {primary_field} -whois",
                                                                  volumes={
                                                                      str(tempPath): {'bind': '/.config/amass',
                                                                                      'mode': 'rw'}},
                                                                  remove=True)
                            elif entity['Entity Type'] == "Autonomous System":
                                container = client.containers.run("caffix/amass:latest",
                                                                  f"intel -src -asn {entity[list(entity)[2]].strip()}"
                                                                  f" -whois",
                                                                  volumes={
                                                                      str(tempPath): {'bind': '/.config/amass',
                                                                                      'mode': 'rw'}},
                                                                  remove=True)
                    jsonFile = tempPath / 'amass.json'
                    if jsonFile.exists():
                        jsonContents = ""
                        with open(jsonFile, 'r') as jsonFileHandler:
                            jsonContents = jsonFileHandler.read()
            except (APIError, docker.errors.ContainerError) as error:
                return "Soomething happened to docker - Cannot continue."
            uid = entity['uid']
            for dictionary in jsonContents.splitlines():
                index_of_child = len(return_result)
                line_dictionary = json.loads(dictionary)
                size = len(line_dictionary['addresses'])
                return_result.append([{'Domain Name': str(line_dictionary['name']),
                                       'Entity Type': 'Domain'},
                                      {uid: {'Resolution': 'Amass Intel Scan', 'Notes': ''}}])
                for ip in range(size):
                    if type(ip_address(line_dictionary['addresses'][ip]['ip'])) is IPv4Address:
                        return_result.append([{'IP Address': str(line_dictionary['addresses'][ip]['ip']),
                                               'Entity Type': 'IP Address'},
                                              {index_of_child: {'Resolution': 'Amass IP Address', 'Notes': ''}}])
                    elif type(ip_address(line_dictionary['addresses'][ip]['ip'])) is IPv6Address:
                        return_result.append([{'IPv6 Address': str(line_dictionary['addresses'][ip]['ip']),
                                               'Entity Type': 'IPv6 Address'},
                                              {index_of_child: {'Resolution': 'Amass IPv6 Address', 'Notes': ''}}])
                    return_result.append([{'AS Number': "AS" + str(line_dictionary['addresses'][ip]['asn']),
                                           'ASN Cidr': str(line_dictionary['addresses'][ip]['cidr']),
                                           'Entity Type': 'Autonomous System'},
                                          {index_of_child: {'Resolution': 'Amass Autonomous System', 'Notes': ''}}])
                    return_result.append([{'Phrase': str(line_dictionary['addresses'][ip]['desc']),
                                           'Entity Type': 'Phrase'},
                                          {index_of_child: {'Resolution': 'Amass Intel Scan Description',
                                                            'Notes': ''}}])
        jsonFileHandler.close()
        return return_result
