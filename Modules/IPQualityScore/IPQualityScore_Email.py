#!/usr/bin/env python3


class IPQualityScore_Email:
    name = "IP Quality Score Email"
    category = "Threats & Malware"
    description = "Find information about the location of a given IP Address or Validate an Email Address"
    originTypes = {'Email Address'}
    resultTypes = {'Phrase', 'Person', 'Email Address'}
    parameters = {'IPQualityScore Private Key': {'description': 'Enter your private key under your profile after '
                                                                'signing up on https://ipqualityscore.com. The limit '
                                                                'per month for free accounts is 5000 lookups.',
                                                 'type': 'String',
                                                 'value': '',
                                                 'global': True}}

    def resolution(self, entityJsonList, parameters):
        import requests
        from requests_futures.sessions import FuturesSession
        from concurrent.futures import as_completed

        return_result = []
        uidList = []
        primaryFields = []
        futures = []

        private_key = parameters['IPQualityScore Private Key']
        url = "https://ipqualityscore.com/api/json/email/private_key/primary_field?timeout=7"
        with FuturesSession(max_workers=15) as session:
            for entity in entityJsonList:
                uidList.append(entity['uid'])
                primary_field = entity[list(entity)[1]].strip()
                primaryFields.append(primary_field)
                crafted_url = url.replace("primary_field", primary_field).replace("private_key", private_key)
                futures.append(session.get(crafted_url))
        for future in as_completed(futures):
            uid = uidList[futures.index(future)]
            try:
                response = future.result().json()
            except requests.exceptions.ConnectionError:
                return "Please check your internet connection"
            if response['success'] != "True" and response['message'] == "You have insufficient credits to make this " \
                                                                        "query. Please contact IPQualityScore " \
                                                                        " support if this error persists.":
                return "Your account doesn't have sufficient credits to complete this operation."
            valid = f"valid: {response['valid']}\n"
            disposable = f"disposable: {response['disposable']}\n"
            smtp_score = f"smtp_score: {response['smtp_score']}\n"
            overall_score = f"overall_score: {response['overall_score']}\n"
            generic = f"generic: {response['generic']}\n"
            common = f"common: {response['common']}\n"
            dns_valid = f"dns_valid: {response['dns_valid']}\n"
            honeypot = f"honeypot: {response['honeypot']}\n"
            deliverability = f"deliverability: {response['deliverability']}\n"
            frequent_complainer = f"frequent_complainer: {response['frequent_complainer']}\n"
            spam_trap_score = f"spam_trap_score: {response['spam_trap_score']}\n"
            catch_all = f"catch_all: {response['catch_all']}\n"
            suspect = f"suspect: {response['suspect']}\n"
            recent_abuse = f"recent_abuse: {response['recent_abuse']}\n"
            fraud_score = f"fraud_score: {response['fraud_score']}\n"
            suggested_domain = f"suggested_domain: {response['suggested_domain']}\n"
            leaked = f"leaked: {response['leaked']}\n"
            return_result.append([{'Phrase': response['request_id'],
                                   'Notes': valid + disposable + smtp_score + overall_score + generic + common +
                                            dns_valid + honeypot + deliverability + frequent_complainer +
                                            spam_trap_score + catch_all + suspect + recent_abuse + fraud_score +
                                            suggested_domain + leaked,
                                   'Entity Type': 'Phrase'},
                                  {uid: {'Resolution': 'IPQualityScore Scan ID', 'Notes': ''}}])
            if response['first_name'] != "":
                return_result.append([{'Full Name': response['first_name'],
                                       'Entity Type': 'Person'},
                                      {uid: {'Resolution': 'IPQualityScore First Name', 'Notes': ''}}])
            if response['sanitized_email'] != primary_field:
                return_result.append([{'Email Address': response['sanitized_email'],
                                       'Entity Type': 'Email Address'},
                                      {uid: {'Resolution': 'IPQualityScore Sanitized Email', 'Notes': ''}}])
        return return_result
