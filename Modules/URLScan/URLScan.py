#!/usr/bin/env python3


class URLScan:
    name = "URLScan Website Search"
    category = "Threats & Malware"
    description = "Find information about a given website"
    originTypes = {'Website', 'Domain'}
    resultTypes = {'IP Address', 'Website', 'Domain', 'Hash'}
    parameters = {'api key': {'description': 'Enter your api key under your profile after'
                                             ' signing up on https://urlscan.io.'
                                             'Above that limit a code 429 will be returned',
                              'type': 'String',
                              'value': ''},
                  'ip results': {'description': 'Enter the number of IP Addresses you want to be returned',
                                 'type': 'String',
                                 'value': '0'},
                  'domain results': {'description': 'Enter the number of Domains you want to be returned',
                                     'type': 'String',
                                     'value': '0'},
                  'hash results': {'description': 'Enter the number of Hashes you want to be returned',
                                   'type': 'String',
                                   'value': '0'},
                  'url results': {'description': 'Enter the number of Urls you want to be returned',
                                  'type': 'String',
                                  'value': '0'}}

    def resolution(self, entityJsonList, parameters):
        import requests
        import json
        import time

        return_result = []
        api_key = parameters['api key']
        hash_results = parameters['hash results']
        domain_results = parameters['domain results']
        ip_results = parameters['ip results']
        url_results = parameters['url results']
        try:
            hash_results = int(hash_results)
            domain_results = int(domain_results)
            ip_results = int(ip_results)
            url_results = int(url_results)
        except ValueError:
            "The value for at least 1 of the parameter fields is not a valid integer."
        for entity in entityJsonList:
            uid = entity['uid']
            primary_field = entity[list(entity)[1]].strip()
            headers = {'API-Key': api_key, 'Content-Type': 'application/json'}
            data = {"url": primary_field, "visibility": "public"}
            response = requests.post('https://urlscan.io/api/v1/scan/', headers=headers, data=json.dumps(data))
            if response.status_code == 429:
                return_result = []
                return "The API Key provided is Invalid or the you are sending requests above the rate limit"
            else:
                while response.status_code == 404:
                    time.sleep(0.5)
                    try:
                        response = requests.post('https://urlscan.io/api/v1/scan/', headers=headers, data=json.dumps(data))
                    except requests.exceptions.ConnectionError:
                        return "Please check your internet connection"
                response = response.json()
                response_uuid = response['uuid']
                result_response = requests.get(f"https://urlscan.io/api/v1/result/{response_uuid}")
                while result_response.status_code == 404 or "message" in result_response:
                    time.sleep(0.5)
                    try:
                        result_response = requests.get(f"https://urlscan.io/api/v1/result/{response_uuid}")
                    except requests.exceptions.ConnectionError:
                        return "Please check your internet connection"
                result_response = result_response.json()
                return_result.append([{'URL': f"https://urlscan.io/api/v1/result/{response_uuid}",
                                       'Entity Type': 'Website',
                                       'Notes': "Request ID: " + str(
                                           result_response['data']['requests'][0]['request']['requestId'])},
                                      {uid: {'Resolution': 'URLScan ID', 'Notes': ''}}])
                for hash in result_response['lists']['hashes']:
                    if hash_results == 0:
                        return_result.append([{'Hash Value': hash,
                                               'Hash Algorithm': "SHA256",
                                               'Entity Type': 'Hash'},
                                              {uid: {'Resolution': 'URLScan SHA25 Hash256', 'Notes': ''}}])
                    else:
                        for i in range(hash_results):
                            return_result.append([{'Hash Value': hash,
                                                   'Hash Algorithm': "SHA256",
                                                   'Entity Type': 'Hash'},
                                                  {uid: {'Resolution': 'URLScan SHA256 Hash', 'Notes': ''}}])
                for ip in result_response['lists']['ips']:
                    if ip_results == 0:
                        return_result.append([{'IP Address': ip,
                                               'Entity Type': 'IP Address'},
                                              {uid: {'Resolution': 'URLScan IP Address', 'Notes': ''}}])
                    else:
                        for i in range(ip_results):
                            return_result.append([{'IP Address': ip,
                                                   'Entity Type': 'IP Address'},
                                                  {uid: {'Resolution': 'URLScan IP Address', 'Notes': ''}}])
                for domain in result_response['lists']['domains']:
                    if domain_results == 0:
                        return_result.append([{'Domain Name': domain,
                                               'Entity Type': 'Domain'},
                                              {uid: {'Resolution': 'URLScan Domains', 'Notes': ''}}])
                    else:
                        for i in range(domain_results):
                            return_result.append([{'Domain Name': domain,
                                                   'Entity Type': 'Domain'},
                                                  {uid: {'Resolution': 'URLScan Domains', 'Notes': ''}}])
                for url in result_response['lists']['urls']:
                    if url_results == 0:
                        return_result.append([{'URL': url,
                                               'Entity Type': 'Website'},
                                              {uid: {'Resolution': 'URLScan URLs', 'Notes': ''}}])
                    else:
                        for i in range(url_results):
                            return_result.append([{'URL': url,
                                                   'Entity Type': 'Website'},
                                                  {uid: {'Resolution': 'URLScan URLs', 'Notes': ''}}])
        return return_result
