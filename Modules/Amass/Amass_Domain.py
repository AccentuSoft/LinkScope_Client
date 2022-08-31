#!/usr/bin/env python3
# User needs to be in docker group or to have root privileges

class Amass_Domain:
    name = "Amass Domain Scan"
    category = "Network Infrastructure"
    description = "Find information about a particular domain. Requires Docker to be installed."
    originTypes = {'Domain'}
    resultTypes = {'IP Address', 'Phrase', 'Autonomous System', 'Domain', 'IPv6 Address'}
    parameters = {'VirusTotal API Key': {'description': 'Enter your api key under your profile after'
                                                        ' signing up on https://virustotal.com.',
                                         'type': 'String',
                                         'value': 'None',
                                         'global': True,
                                         'default': 'None'},
                  'AlienVault API Key': {'description': 'Enter your api key under your profile after'
                                                        ' signing up on https://otx.alienvault.com.',
                                         'type': 'String',
                                         'value': 'None',
                                         'global': True,
                                         'default': 'None'},
                  'BinaryEdge API Key': {'description': 'Enter your api key under your profile after'
                                                        ' signing up on https://app.binaryedge.com.',
                                         'type': 'String',
                                         'value': 'None',
                                         'global': True,
                                         'default': 'None'},
                  'C99 API Key': {'description': 'Enter your api key under your profile after'
                                                 ' signing up on https://c99.nl.',
                                  'type': 'String',
                                  'value': 'None',
                                  'global': True,
                                  'default': 'None'},
                  'Censys API Key': {'description': 'Enter your api key under your profile after'
                                                    ' signing up on https://censys.io.',
                                     'type': 'String',
                                     'value': 'None',
                                     'global': True,
                                     'default': 'None'},
                  'Chaos API Key': {'description': 'Enter your api key under your profile after'
                                                   ' signing up on https://chaos.projectdiscovery.io.',
                                    'type': 'String',
                                    'value': 'None',
                                    'global': True,
                                    'default': 'None'},
                  'Cloudflare API Key': {'description': 'Enter your api key under your profile after'
                                                        ' signing up on https://cloudflare.com.',
                                         'type': 'String',
                                         'value': 'None',
                                         'global': True,
                                         'default': 'None'},
                  'DNSDB API Key': {'description': 'Enter your api key under your profile after'
                                                   ' signing up on https://dnsdb.info.',
                                    'type': 'String',
                                    'value': 'None',
                                    'global': True,
                                    'default': 'None'},
                  'GitHub API Key': {'description': 'Enter your api key under your profile after'
                                                    ' signing up on https://github.com.',
                                     'type': 'String',
                                     'value': 'None',
                                     'global': True,
                                     'default': 'None'},
                  'Hunter API Key': {'description': 'Enter your api key under your profile after'
                                                    ' signing up on https://hunter.io.',
                                     'type': 'String',
                                     'value': 'None',
                                     'global': True,
                                     'default': 'None'},
                  'IPInfo Access Token': {'description': 'Enter your api key under your profile after'
                                                         ' signing up on https://ipinfo.io.',
                                          'type': 'String',
                                          'value': 'None',
                                          'global': True,
                                          'default': 'None'},
                  'NetworksDB API Key': {'description': 'Enter your api key under your profile after'
                                                        ' signing up on https://networksdb.io.',
                                         'type': 'String',
                                         'value': 'None',
                                         'global': True,
                                         'default': 'None'},
                  'PassiveTotal API Key': {'description': 'Enter your api key under your profile after'
                                                          ' signing up on https://passivetotal.com .',
                                           'type': 'String',
                                           'value': 'None',
                                           'global': True,
                                           'default': 'None'},
                  'ReconDev API Key': {'description': 'Enter your api key under your profile after'
                                                      ' signing up on https://recon.dev.',
                                       'type': 'String',
                                       'value': 'None',
                                       'global': True,
                                       'default': 'None'},
                  'SecurityTrails API Key': {'description': 'Enter your api key under your profile after'
                                                            ' signing up on https://securitytrails.com.',
                                             'type': 'String',
                                             'value': 'None',
                                             'global': True,
                                             'default': 'None'},
                  'Shodan API Key': {'description': 'Enter your api key under your profile after'
                                                    ' signing up on https://shodan.io.',
                                     'type': 'String',
                                     'value': 'None',
                                     'global': True,
                                     'default': 'None'},
                  'Spyse API Key': {'description': 'Enter your api key under your profile after'
                                                   ' signing up on https://spyse.com.',
                                    'type': 'String',
                                    'value': 'None',
                                    'global': True,
                                    'default': 'None'},
                  'ThreatBook API Key': {'description': 'Enter your api key under your profile after'
                                                        ' signing up on https://threatbook.cn.',
                                         'type': 'String',
                                         'value': 'None',
                                         'global': True,
                                         'default': 'None'},
                  'Umbrella API Key': {'description': 'Enter your api key under your profile after'
                                                      ' signing up on https://umbrella.cisco.com.',
                                       'type': 'String',
                                       'value': 'None',
                                       'global': True,
                                       'default': 'None'},
                  'URLScan API Key': {'description': 'Enter your api key under your profile after'
                                                     ' signing up on https://urlscan.io.',
                                      'type': 'String',
                                      'value': 'None',
                                      'global': True,
                                      'default': 'None'},
                  'WhoisXMLAPI API Key': {'description': 'Enter your api key under your profile after'
                                                         ' signing up on https://whoisxmlapi.com.',
                                          'type': 'String',
                                          'value': 'None',
                                          'global': True,
                                          'default': 'None'},
                  'ZETAlytics API Key': {'description': 'Enter your api key under your profile after'
                                                        ' signing up on https://zetalytics.com.',
                                         'type': 'String',
                                         'value': 'None',
                                         'global': True,
                                         'default': 'None'},
                  'ZoomEye API Key': {'description': 'Please Enter the Username and password with a space '
                                                     'in between',
                                      'type': 'String',
                                      'value': 'None',
                                      'global': True,
                                      'default': 'None'},
                  'FacebookCT API Key': {'description': 'Please Enter the api key and secret with a space '
                                                        'in between. Obtain them at https://developer.facebook.com',
                                         'type': 'String',
                                         'value': 'None',
                                         'global': True,
                                         'default': 'None'},
                  'Twitter API Key': {'description': 'Please Enter the api key and secret with a space '
                                                     'in between. Obtain them at https://developer.twitter.com',
                                      'type': 'String',
                                      'value': 'None',
                                      'global': True,
                                      'default': 'None'},
                  'ReconDev.free API Key': {
                      'description':
                          'Please Enter the api key under your profile after signing up on https://recon.dev',
                      'type': 'String',
                      'value': 'None',
                      'global': True,
                      'default': 'None'},
                  'ReconDev.paid API Key': {
                      'description':
                          'Please Enter the api key under your profile after signing up on https://recon.dev',
                      'type': 'String',
                      'value': 'None',
                      'global': True,
                      'default': 'None'}}

    def resolution(self, entityJsonList, parameters):
        from pathlib import Path
        import json
        from ipaddress import ip_address, IPv4Address, IPv6Address
        import docker
        import tempfile
        from docker.errors import APIError

        return_result = []
        # Generate Config as a temporary file:
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
            for parameter in self.parameters:
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
            path_to_config = Path(config.name).name
            config.seek(0)
            for entity in entityJsonList:
                primary_field = entity["Domain Name"].strip()
                try:
                    client = docker.from_env()
                    container = client.containers.run("caffix/amass:latest",
                                                      f"enum -src -d {primary_field} "
                                                      f"-config /.config/amass/{path_to_config}",
                                                      volumes={
                                                          str(tempPath): {'bind': '/.config/amass',
                                                                          'mode': 'rw'}},
                                                      remove=True)
                    jsonFile = tempPath / 'amass.json'
                    jsonContents = ""
                    if jsonFile.exists():
                        with open(jsonFile, 'r') as jsonFileHandler:
                            jsonContents = jsonFileHandler.read()
                    client.close()
                except (APIError, docker.errors.ContainerError) as error:
                    return "Something happened to the docker container - Cannot continue: " + str(error)
                uid = entity['uid']
                for dictionary in jsonContents.splitlines():
                    index_of_child = len(return_result)
                    line_dictionary = json.loads(dictionary)
                    size = len(line_dictionary['addresses'])
                    return_result.append([{'Domain Name': str(line_dictionary['name']),
                                           'Entity Type': 'Domain'},
                                          {uid: {'Resolution': 'Amass Domain Scan', 'Notes': ''}}])
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
                                              {index_of_child: {'Resolution': 'Amass Domain Scan Description',
                                                                'Notes': ''}}])
            config.close()
        return return_result
