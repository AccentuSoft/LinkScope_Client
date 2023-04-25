#!/usr/bin/env python3


class URLScan:
    name = "URLScan Website Search"
    category = "Threats & Malware"
    description = "Find information about a given website"
    originTypes = {'Website', 'Domain'}
    resultTypes = {'IP Address', 'Website', 'Domain', 'Hash'}
    parameters = {'URLScan API Key': {'description': 'Enter your api key under your profile after '
                                                     'signing up on https://urlscan.io. '
                                                     'Requests beyond the limit will fail with HTTP '
                                                     'status code 429.',
                                      'type': 'String',
                                      'global': True,
                                      'value': ''}
                  }

    def resolution(self, entityJsonList, parameters):
        import requests
        import json
        import time

        return_result = []
        api_key = parameters['URLScan API Key']
        for entity in entityJsonList:
            uid = entity['uid']
            primary_field = entity[list(entity)[1]].strip()
            headers = {'API-Key': api_key, 'Content-Type': 'application/json'}
            data = {"url": primary_field, "visibility": "public"}
            response = requests.post('https://urlscan.io/api/v1/scan/', headers=headers, data=json.dumps(data))
            if response.status_code == 429:
                return "The API Key provided is Invalid or the you are sending requests above the rate limit"
            while response.status_code == 404:
                time.sleep(0.5)
                try:
                    response = requests.post('https://urlscan.io/api/v1/scan/', headers=headers,
                                             data=json.dumps(data))
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
            return_result.extend(
                [{'Hash Value': hash_result,
                  'Hash Algorithm': "SHA256",
                  'Entity Type': 'Hash'},
                 {uid: {'Resolution': 'URLScan SHA25 Hash256', 'Notes': ''}}]
                for hash_result in result_response['lists']['hashes']
            )
            return_result.extend(
                [{'IP Address': ip, 'Entity Type': 'IP Address'},
                 {uid: {'Resolution': 'URLScan IP Address', 'Notes': ''}}]
                for ip in result_response['lists']['ips']
            )
            return_result.extend(
                [{'Domain Name': domain, 'Entity Type': 'Domain'},
                 {uid: {'Resolution': 'URLScan Domains', 'Notes': ''}}]
                for domain in result_response['lists']['domains']
            )
            return_result.extend(
                [{'URL': url, 'Entity Type': 'Website'},
                 {uid: {'Resolution': 'URLScan URLs', 'Notes': ''}}]
                for url in result_response['lists']['urls']
            )
        return return_result
