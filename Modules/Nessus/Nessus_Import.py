#!/usr/bin/python


class Nessus_Import:
    name = "Nessus Import"
    description = "Nessus vulnerability scanner importer"
    originTypes = {'Document'}
    resultTypes = {'Phrase', 'IP Address', 'Operating System', 'Port'}
    parameters = {}

    def getVulnerabilities(self, xml_content):
        from lxml import etree

        vulnerabilities = dict()
        single_params = ["agent", "cvss3_base_score", "cvss3_temporal_score", "cvss3_temporal_vector",
                         "cvss3_vector",
                         "cvss_base_score", "cvss_temporal_score", "cvss_temporal_vector", "cvss_vector",
                         "description",
                         "exploit_available", "exploitability_ease", "exploited_by_nessus", "fname", "in_the_news",
                         "patch_publication_date", "plugin_modification_date", "plugin_name",
                         "plugin_publication_date",
                         "plugin_type", "script_version", "see_also", "solution", "synopsis",
                         "vuln_publication_date",
                         "compliance",
                         "{https://www.nessus.org/cm}compliance-check-id",
                         "{https://www.nessus.org/cm}compliance-check-name",
                         "{https://www.nessus.org/cm}audit-file",
                         "{https://www.nessus.org/cm}compliance-info",
                         "{https://www.nessus.org/cm}compliance-result",
                         "{https://www.nessus.org/cm}compliance-see-also"]
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
                                    compliance_check_id = vulner_struct[
                                        '{https://www.nessus.org/cm}compliance-check-id']
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
        return_result = []
        for entity in entityJsonList:
            uid = entity['uid']
            fileDirectory = entity[list(entity)[2]]
            fileHandler = open(fileDirectory, 'r')
            xml_content = fileHandler.read()
            fileHandler.close()
            vulners = self.getVulnerabilities(xml_content)
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
