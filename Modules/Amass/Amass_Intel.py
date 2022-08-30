#!/usr/bin/env python3
# User needs to be in docker group or have root privileges

class Amass_Intel:
    name = "Amass Intel Scan"
    category = "Network Infrastructure"
    description = "Find information about a particular domain"
    originTypes = {'Domain', 'IP Address', 'Autonomous System'}
    resultTypes = {'Domain'}
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
            path_to_config = "/" + Path(config.name).name
            config.seek(0)
            for entity in entityJsonList:
                primary_field = entity[list(entity)[1]].strip()
                try:
                    client = docker.from_env()
                    if entity['Entity Type'] == "Domain":
                        container = client.containers.run("caffix/amass:latest",
                                                          f"intel -whois -d {primary_field} -config /.config/amass"
                                                          f"{path_to_config}",
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
                                                          f"intel -addr {primary_field} -config "
                                                          f"/.config/amass{path_to_config}",
                                                          volumes={
                                                              str(tempPath): {'bind': '/.config/amass',
                                                                              'mode': 'rw'}},
                                                          remove=True)
                    elif entity['Entity Type'] == "Autonomous System":
                        if primary_field.startswith('AS'):
                            primary_field = primary_field[2:]
                        container = client.containers.run("caffix/amass:latest",
                                                          f"intel -asn {primary_field}"
                                                          f" -config /.config/amass{path_to_config}",
                                                          volumes={
                                                              str(tempPath): {'bind': '/.config/amass',
                                                                              'mode': 'rw'}},
                                                          remove=True)
                    textFile = tempPath / 'amass.txt'
                    textContents = ""
                    if textFile.exists():
                        with open(textFile, 'r') as textFileHandler:
                            textContents = textFileHandler.read()

                    client.close()
                except (APIError, docker.errors.ContainerError) as error:
                    return "Something happened to the docker container - Cannot continue: " + str(error)
                uid = entity['uid']
                for newDomain in textContents.splitlines():
                    return_result.append([{'Domain Name': newDomain.strip(),
                                           'Entity Type': 'Domain'},
                                          {uid: {'Resolution': 'Amass Intel Scan', 'Notes': ''}}])

            config.close()
        return return_result
