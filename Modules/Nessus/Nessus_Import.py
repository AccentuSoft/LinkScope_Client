#!/usr/bin/python


class Nessus_Import:
    name = "Nessus Import"
    description = "Import .nessus report findings"
    originTypes = {'Document'}
    resultTypes = {'Finding', 'Port', 'IP Address', 'IPv6 Address', 'Phrase', 'CVE'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        from pathlib import Path
        from defusedxml.ElementTree import parse

        return_results = []

        for entity in entityJsonList:
            reportUID = entity['uid']
            filePath = Path(parameters['Project Files Directory']) / entity['File Path']
            root = parse(str(filePath), forbid_dtd=True,
                         forbid_entities=True, forbid_external=True).getroot()
            report = root.find('Report')

            if report is None:
                return "Report was not properly generated for the scan."

            hostAddress = ""
            for reportHost in report:
                for tag in reportHost.find('HostProperties'):
                    if tag.attrib['name'] == "host-ip":
                        hostAddress = tag.text
                        if ":" in hostAddress:
                            return_results.append([{
                                'IP Address': hostAddress,
                                'Entity Type': 'IP Address'},
                                {reportUID: {'Resolution': 'Nessus Scan', 'Notes': ''}}])
                        else:
                            return_results.append([{
                                'IPv6 Address': hostAddress,
                                'Entity Type': 'IPv6 Address'},
                                {reportUID: {'Resolution': 'Nessus Scan', 'Notes': ''}}])
                for reportItem in reportHost.findall('ReportItem'):
                    childIndex = len(return_results)
                    if reportItem.attrib['port'] == '0':
                        cvssScore = reportItem.find('cvss_base_score').text \
                            if reportItem.find('cvss_base_score') is not None else "0"
                        cvssVector = reportItem.find('cvss_vector').text \
                            if reportItem.find('cvss_vector') is not None else "N/A"
                        return_results.append([{
                            'Issue Synopsis': reportItem.find('synopsis').text,
                            'Solution': reportItem.find('solution').text,
                            'CVSS2 Score': cvssScore,
                            'CVSS2 Vector': cvssVector,
                            'Entity Type': 'Finding',
                            'Notes': reportItem.find('plugin_output').text
                            if reportItem.find('plugin_output') is not None else ""},
                            {childIndex: {'Resolution': 'Nessus Scan', 'Notes': ''}}])

                        riskFactor = reportItem.find('risk_factor').text

                        return_results.append([{
                            'Phrase': "Risk Factor: " + riskFactor,
                            'Entity Type': 'Phrase'},
                            {len(return_results) - 1: {'Resolution': 'Nessus Scan', 'Notes': ''}}])

                        cve = reportItem.find('cve').text if reportItem.find('cve') is not None else ""

                        if cve != "":
                            return_results.append([{
                                'CVE': cve,
                                'Entity Type': 'CVE'},
                                {len(return_results) - 1: {'Resolution': 'Nessus Scan', 'Notes': ''}}])

                    else:
                        return_results.append([{
                            'Port': hostAddress + "|" + reportItem.attrib['port'] + "|" + reportItem.attrib['protocol'],
                            'Entity Type': 'Port'},
                            {childIndex: {'Resolution': 'Nessus Scan', 'Notes': ''}}])

                        cvssScore = reportItem.find('cvss_base_score').text \
                            if reportItem.find('cvss_base_score') is not None else "0"
                        cvssVector = reportItem.find('cvss_vector').text \
                            if reportItem.find('cvss_vector') is not None else "N/A"
                        return_results.append([{
                            'Issue Synopsis': reportItem.find('synopsis').text,
                            'Solution': reportItem.find('solution').text,
                            'CVSS2 Score': cvssScore,
                            'CVSS2 Vector': cvssVector,
                            'Entity Type': 'Finding',
                            'Notes': reportItem.find('plugin_output').text
                            if reportItem.find('plugin_output') is not None else ""},
                            {len(return_results) - 1: {'Resolution': 'Nessus Scan', 'Notes': ''}}])

                        riskFactor = reportItem.find('risk_factor').text

                        return_results.append([{
                            'Phrase': "Risk Factor: " + riskFactor,
                            'Entity Type': 'Phrase'},
                            {len(return_results) - 1: {'Resolution': 'Nessus Scan', 'Notes': ''}}])

                        cve = reportItem.find('cve').text if reportItem.find('cve') is not None else ""

                        if cve != "":
                            return_results.append([{
                                'CVE': cve,
                                'Entity Type': 'CVE'},
                                {len(return_results) - 1: {'Resolution': 'Nessus Scan', 'Notes': ''}}])
        return return_results
