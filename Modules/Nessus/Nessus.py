#!/usr/bin/python


class Nessus:
    name = "Nessus"
    description = "Nessus vulnerability scanner"
    originTypes = {'Website', 'IP Address'}
    resultTypes = {'Phrase', 'IP Address'}
    parameters = {
        'Nessus Base URL': {'description': 'Enter the url where Nessus starts on your computer or company network '
                                           'e.g: https://127.0.0.1:8834/',
                            'type': 'String',
                            'default': 'https://127.0.0.1:8834',
                            'value': ''},
        'Nessus Username': {'description': 'Enter the username used for Nessus.',
                            'type': 'String',
                            'value': ''},
        'Nessus Password': {'description': 'Enter the password used for Nessus.',
                            'type': 'String',
                            'value': ''},
        'Scan Type': {'description': 'Enter the type of scan to be used for Nessus.',
                      'type': 'SingleChoice',
                      'value': {'Host Discovery', 'Basic Network Scan', 'Web Application Testing',
                                'Credentials Patch Audit', 'Last Scan', 'Intel AMT Security Bypass',
                                'Spectre and Meltdown', 'WannaCry Ransomware', 'Ripple20 Remote Scan',
                                'Zerologon Remote Scan', '2020 Threat Landscape Retrospective (TLR)',
                                'Solorigate'}},
        'Result Severity': {'description': 'Enter the password used for Nessus.',
                            'type': 'String',
                            'value': ''}}

    def get_vulners_from_xml(self, xml_content):
        from lxml import etree
        vulnerabilities = dict()
        single_params = ["agent", "cvss3_base_score", "cvss3_temporal_score", "cvss3_temporal_vector", "cvss3_vector",
                         "cvss_base_score", "cvss_temporal_score", "cvss_temporal_vector", "cvss_vector", "description",
                         "exploit_available", "exploitability_ease", "exploited_by_nessus", "fname", "in_the_news",
                         "patch_publication_date", "plugin_modification_date", "plugin_name", "plugin_publication_date",
                         "plugin_type", "script_version", "see_also", "solution", "synopsis", "vuln_publication_date",
                         "compliance",
                         "{http://www.nessus.org/cm}compliance-check-id",
                         "{http://www.nessus.org/cm}compliance-check-name",
                         "{http://www.nessus.org/cm}audit-file",
                         "{http://www.nessus.org/cm}compliance-info",
                         "{http://www.nessus.org/cm}compliance-result",
                         "{http://www.nessus.org/cm}compliance-see-also"]
        root = etree.fromstring(text=xml_content, parser=etree.XMLParser(huge_tree=True))
        for block in root:
            if block.tag == "Report":
                for report_host in block:
                    host_properties_dict = dict()
                    for report_item in report_host:
                        if report_item.tag == "HostProperties":
                            for host_properties in report_item:
                                host_properties_dict[host_properties.attrib['name']] = host_properties.text
                    for report_item in report_host:
                        if 'pluginName' in report_item.attrib:
                            vulner_struct = dict()
                            vulner_struct['port'] = report_item.attrib['port']
                            vulner_struct['pluginName'] = report_item.attrib['pluginName']
                            vulner_struct['pluginFamily'] = report_item.attrib['pluginFamily']
                            vulner_struct['pluginID'] = report_item.attrib['pluginID']
                            vulner_struct['svc_name'] = report_item.attrib['svc_name']
                            vulner_struct['protocol'] = report_item.attrib['protocol']
                            vulner_struct['severity'] = report_item.attrib['severity']
                            for param in report_item:
                                if param.tag == "risk_factor":
                                    risk_factor = param.text
                                    vulner_struct['host'] = report_host.attrib['name']
                                    vulner_struct['riskFactor'] = risk_factor
                                elif param.tag == "plugin_output":
                                    if "plugin_output" not in vulner_struct:
                                        vulner_struct["plugin_output"] = list()
                                    if param.text not in vulner_struct["plugin_output"]:
                                        vulner_struct["plugin_output"].append(
                                            param.text)
                                else:
                                    if param.tag not in single_params:
                                        if param.tag not in vulner_struct:
                                            vulner_struct[param.tag] = list()
                                        if not isinstance(vulner_struct[param.tag], list):
                                            vulner_struct[param.tag] = [
                                                vulner_struct[param.tag]]
                                        if param.text not in vulner_struct[param.tag]:
                                            vulner_struct[param.tag].append(
                                                param.text)
                                    else:
                                        vulner_struct[param.tag] = param.text
                            for param in host_properties_dict:
                                vulner_struct[param] = host_properties_dict[param]
                            compliance_check_id = ""
                            if 'compliance' in vulner_struct:
                                if vulner_struct['compliance'] == 'true':
                                    compliance_check_id = vulner_struct['{http://www.nessus.org/cm}compliance-check-id']
                            if compliance_check_id == "":
                                vulner_id = vulner_struct['host'] + "|" + vulner_struct['port'] + "|" + \
                                            vulner_struct['protocol'] + \
                                            "|" + vulner_struct['pluginID']
                            else:
                                vulner_id = vulner_struct['host'] + "|" + vulner_struct['port'] + "|" + \
                                            vulner_struct['protocol'] + "|" + vulner_struct['pluginID'] + "|" + \
                                            compliance_check_id
                            if vulner_id not in vulnerabilities:
                                vulnerabilities[vulner_id] = vulner_struct
        return vulnerabilities

    def resolution(self, entityJsonList, parameters):
        import requests
        import json
        import time
        import urllib3
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.common.exceptions import SessionNotCreatedException
        from selenium.webdriver.support import expected_conditions as EC
        fireFoxOptions = webdriver.FirefoxOptions()

        # Note that certificate verification is disabled for this module, as self-hosted
        #   instances of Nessus are not expected to have valid certificates.

        # Variables
        driver = webdriver.Firefox(options=fireFoxOptions)
        wait = WebDriverWait(driver, 5)
        nessusBaseURL = parameters['Nessus Base URL']
        if not nessusBaseURL.endswith('/'):
            nessusBaseURL = nessusBaseURL + "/"
        nessusUsername = parameters['Nessus Username']
        nessusPassword = parameters['Nessus Password']
        scanType = parameters['Scan Type']
        resultSeverity = parameters['Result Severity']
        try:
            resultSeverity = int(resultSeverity)
        except ValueError:
            return "Enter a valid number in the result severity field"
            # Grab the token
        try:
            crafted_url = nessusBaseURL + "session"
            tokenParameters = {'username': nessusUsername,
                               'password': nessusPassword}
            try:
                response = requests.post(
                    url=crafted_url, data=tokenParameters, verify=False)  # nosec
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"
            except requests.exceptions.InvalidURL:
                return "Please check that your Nessus Base URL is correct"
            jsonData = response.json()
            token = str("token=" + jsonData['token'])
        except KeyError:
            return "Wrong parameters provided"
        # In our case, we're asking for a:
        #   - .Nessus export
        #   - Only requesting certain fields based on the users parameters
        payload = {
            "format": "nessus",
            "reportContents": {
                "csvColumns": {
                    "id": True,
                    "cve": True,
                    "cvss": True,
                    "risk": True,
                    "hostname": True,
                    "protocol": True,
                    "port": True,
                    "plugin_name": False,
                    "synopsis": False,
                    "description": False,
                    "solution": False,
                    "see_also": False,
                    "plugin_output": True,
                    "stig_severity": False,
                    "cvss3_base_score": False,
                    "cvss_temporal_score": False,
                    "cvss3_temporal_score": False,
                    "risk_factor": False,
                    "references": False,
                    "plugin_information": False,
                    "exploitable_with": False
                }
            },
            "extraFilters": {
                "host_ids": [],
                "plugin_ids": []
            },
            "filter.0.quality": "eq",
            "filter.0.filter": "severity",
            "filter.0.value": resultSeverity
        }

        # Turn off TLS warnings
        urllib3.disable_warnings()

        return_result = []
        uidList = []
        targets = ""
        if scanType == "Last Scan":
            # Grab the token
            try:
                crafted_url = nessusBaseURL + "session"
                tokenParameters = {
                    'username': nessusUsername, 'password': nessusPassword}
                try:
                    response = requests.post(
                        url=crafted_url, data=tokenParameters, verify=False)  # nosec
                except requests.exceptions.ConnectionError:
                    return "Please check your internet connection"
                jsonData = response.json()
                token = str("token=" + jsonData['token'])
            except KeyError:
                return "Wrong parameters provided"
            crafted_url = nessusBaseURL + "scans"
            print(crafted_url)
            headers = {'X-Cookie': token,
                       'Content-type': 'application/json', 'Accept': 'text/plain'}
            statusCheck = requests.get(
                url=crafted_url, headers=headers, verify=False)  # nosec
            data = statusCheck.json()
            while data['scans'][0]['status'] != 'completed':
                time.sleep(0.1)
                try:
                    statusCheck = requests.get(
                        url=crafted_url, headers=headers, verify=False)  # nosec
                except requests.exceptions.ConnectionError:
                    return "Please check your internet connection"
                data = statusCheck.json()

            print(data)
            ID = data['scans'][0]['id']
            # NAME = data['scans'][0]['name']

            # Call the POST /export function to collect details for each scan
            crafted_url = nessusBaseURL + "scans/" + str(ID) + "/export"

            # Pass the POST request in json format. Two items are returned, file and token
            jsonPayload = json.dumps(payload)
            try:
                response = requests.post(
                    url=crafted_url, headers=headers, data=jsonPayload, verify=False)  # nosec
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"
            jsonData = response.json()
            print(jsonData)
            scanFile = str(jsonData['file'])

            # Use the file just received and check to see if it's 'ready', otherwise sleep until and try again
            status = "loading"
            while status != 'ready':
                crafted_url = nessusBaseURL + "scans/" + \
                              str(ID) + "/export/" + scanFile + "/status"
                try:
                    statusCheck = requests.get(
                        url=crafted_url, headers=headers, verify=False)  # nosec
                except requests.exceptions.ConnectionError:
                    return "Please check your internet connection"
                data = statusCheck.json()
                print(data)
                if data['status'] == 'ready':
                    status = 'ready'
                else:
                    time.sleep(0.1)

            # Now that the report is ready, download
            crafted_url = nessusBaseURL + "scans/" + str(ID) + "/export/" + scanFile + "/download"
            try:
                Download = requests.get(
                    url=crafted_url, headers=headers, verify=False)  # nosec
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"
            dataBack = Download.text

            return return_result
        elif scanType == "Host Discovery":
            scan_uid = "bbd4f805-3966-d464-b2d1-0079eb89d69708c3a05ec2812bcf"
        elif scanType == "Basic Network Scan":
            scan_uid = "731a8e52-3ea6-a291-ec0a-d2ff0619c19d7bd788d6be818b65"
        elif scanType == "Web Application Testing":
            scan_uid = "c3cbcd46-329f-a9ed-1077-554f8c2af33d0d44f09d736969bf"
        elif scanType == "Credentials Patch Audit":
            scan_uid = "0625147c-30fe-d79f-e54f-ce7ccd7523e9b63d84cb81c23c2f"
        elif scanType == "Intel AMT Security Bypass":
            scan_uid = "3f514e0e-66e0-8ea2-b6e7-d2d86b526999a93a89944d19e1f1"
        elif scanType == "Spectre and Meltdown":
            scan_uid = "5dd44847-3c6a-412c-b916-6cc21dd80785df97ab44910aceee"
        elif scanType == "WannaCry Ransomware":
            scan_uid = "861a8b95-f04c-40b0-ece6-263b1bec457c09cfc122c9666645"
        elif scanType == "Ripple20 Remote Scan":
            scan_uid = "139a2145-95e3-0c3f-f1cc-761db860e4eed37b6eee77f9e101"
        elif scanType == "Solorigate":
            scan_uid = "ebb66f38-ea88-e1fe-eb5c-116ebc514f723d842f7882f0b7e1"
        elif scanType == "Zerologon Remote Scan":
            scan_uid = "36191558-0c2f-83fb-f036-97865e2adbc168980dae38867ad9"
        elif scanType == "2020 Threat Landscape Retrospective (TLR)":
            scan_uid = "9125f3af-1ba3-e6ce-4ab6-bc04f9c323fd3cef959b11f41b81"
        elif scanType == "ProxyLogon : MS Exchange":
            scan_uid = "2d429fb8-2182-2584-c4f0-a57da3db12ef4abed9ea6b5c3937"
        elif scanType == "PrintNightmare":
            scan_uid = "d00e471d-c26b-7e1e-0f2b-db0f8d924eb460452a19b5327dcf"
        elif scanType == "Active Directory Starter Scan":
            scan_uid = "8b5d14bc-f33e-cbc1-ef33-bf6c40eb568f1401448c08dbfd88"
        elif scanType == "Internal PCI Network Scan":
            scan_uid = "e460ea7c-7916-d001-51dc-e43ef3168e6e20f1d97bdebf4a49"
        elif scanType == "Policy Compliance Auditing":
            scan_uid = "40345bfc-48be-37bc-9bce-526bdce37582e8fee83bcefdc746"
        elif scanType == "SCAP and OVAL Auditing":
            scan_uid = "fb9cbabc-af67-109e-f023-1e0d926c9e5925eee7a0aa8a8bd1"
        elif scanType == "PCI Quarterly External Scan":
            scan_uid = "cfc46c2d-30e7-bb2b-3b92-c75da136792d080c1fffcc429cfd"
        for entity in entityJsonList:
            uid = entity['uid']
            targets = targets + " " + entity[list(entity)[1]].strip()
            driver.get(nessusBaseURL)
            wait.until(EC.element_to_be_clickable((
                By.XPATH, "/html/body/div/form/button")))
            element = driver.find_element_by_xpath(
                "/html/body/div/form/div[1]/input")
            element.send_keys(nessusUsername)
            element = driver.find_element_by_xpath(
                "/html/body/div/form/div[2]/input")
            element.send_keys(nessusPassword)
            element = driver.find_element_by_xpath("/html/body/div/form/button")
            element.click()
            scanSelectedURL = nessusBaseURL + "#/scans/reports/new/" + scan_uid + "/settings/basic/general"
            driver.get(scanSelectedURL)
            wait.until(EC.visibility_of_element_located((
                By.XPATH, "/html/body/section[3]/section[3]/section/form/div[1]/"
                "div/div/div[1]/section/div[1]/div[1]/div[1]/div[1]/div/input")))
            element = driver.find_element_by_xpath(
                "/html/body/section[3]/section[3]/section/form/div[1]/"
                "div/div/div[1]/section/div[1]/div[1]/div[1]/div[1]/div/input")
            element.send_keys(f"AccentuSoft LinkScope Automated Scanning {targets} {scanType}")
            element = driver.find_element_by_xpath(
                "/html/body/section[3]/section[3]/section/form/div[1]/"
                "div/div/div[1]/section/div[1]/div[1]/div[1]/div[5]/div/textarea")
            element.send_keys(str(targets))
            element = driver.find_element_by_xpath("/html/body/section[3]/section[3]/section/form/div[2]/ul/li")
            element.click()

            # Get Results
            crafted_url = nessusBaseURL + "scans"
            headers = {'X-Cookie': token,
                       'Content-type': 'application/json', 'Accept': 'text/plain'}
            try:
                statusCheck = requests.get(
                    url=crafted_url, headers=headers, verify=False)  # nosec
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"
            data = statusCheck.json()
            while data['scans'][0]['status'] != 'completed':
                time.sleep(0.5)
                try:
                    statusCheck = requests.get(
                        url=crafted_url, headers=headers, verify=False)  # nosec
                except requests.exceptions.ConnectionError:
                    return "Please check your internet connection"
                data = statusCheck.json()
            ID = data['scans'][0]['id']
            # NAME = data['scans'][0]['name']

            # Main loop for the program
            # Call the POST /export function to collect details for each scan
            crafted_url = nessusBaseURL + "scans/" + str(ID) + "/export"

            # Pass the POST request in json format. Two items are returned, file and token
            jsonPayload = json.dumps(payload)
            try:
                response = requests.post(
                    url=crafted_url, headers=headers, data=jsonPayload, verify=False)  # nosec
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"
            jsonData = response.json()
            scanFile = str(jsonData['file'])

            # Use the file just received and check to see if it's 'ready', otherwise sleep for timeToSleep seconds
            # and try again
            status = "loading"
            while status != 'ready':
                crafted_url = nessusBaseURL + "scans/" + \
                              str(ID) + "/export/" + scanFile + "/status"
                try:
                    statusCheck = requests.get(
                        url=crafted_url, headers=headers, verify=False)  # nosec
                except requests.exceptions.ConnectionError:
                    return "Please check your internet connection"
                data = statusCheck.json()
                if data['status'] == 'ready':
                    status = 'ready'
                else:
                    time.sleep(0.1)

            # Now that the report is ready, download
            crafted_url = nessusBaseURL + "scans/" + str(ID) + "/export/" + scanFile + "/download"
            try:
                Download = requests.get(url=crafted_url, headers=headers, verify=False)  # nosec
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"
            xml_content = Download.text
            vulners = self.get_vulners_from_xml(xml_content)
            for ip in list(vulners):
                ipFormated = ip.split("|")
                if vulners[ip].get('traceroute-hop-0') is not None:
                    index_of_child = len(return_result)
                    return_result.append([{
                        'IP Address': vulners[ip]['traceroute-hop-0'],
                        'Entity Type': 'IP Address'},
                        {uid: {'Resolution': 'Nessus Scan Traceroute hop 0', 'Notes': ''}}])
                    index_of_child_of_child = len(return_result)
                else:
                    index_of_child = uid
                return_result.append([{
                    'IP Address': f"{ipFormated[0]}",
                    'Entity Type': 'IP Address'},
                    {index_of_child: {'Resolution': 'Nessus Scan Host', 'Notes': ''}}])
                index_of_child_of_child_of_child = len(return_result)
                return_result.append([{
                    'Port': f"{ipFormated[0]}:{ipFormated[1]}:{vulners[ip]['protocol']}",
                    'Notes': f"Severity: {vulners[ip]['severity']}",
                    'Entity Type': 'Port'},
                    {index_of_child_of_child: {'Resolution': 'Nessus Scan host ports', 'Notes': ''}}])
                if vulners[ip]['os']:
                    return_result.append([{
                        'OS Name': vulners[ip]['os'],
                        'Entity Type': 'Operating System'},
                        {index_of_child_of_child_of_child: {'Resolution': 'Nessus Scan host OS', 'Notes': ''}}])
                if vulners['ip'].get('cpe-1') is not None:
                    cpe = vulners[ip]['cpe-1'].split("->")
                    return_result.append([{
                        'Phrase': cpe[1],
                        'Notes': cpe[0],
                        'Entity Type': 'Phrase'},
                        {index_of_child_of_child_of_child: {'Resolution': 'Nessus Scan host cpe', 'Notes': ''}}])
        return return_result
