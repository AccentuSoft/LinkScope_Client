#!/usr/bin/env python3


class CertificateInfo:
    name = "Analyze Website Certificate"
    category = "Network Infrastructure"
    description = "Get certificate information from the certificate of a certain website."
    originTypes = {'Website'}
    resultTypes = {'Phrase', 'Website', 'Domain', 'Country', 'Organization', 'Address', 'Date'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import ssl
        import socket

        returnResults = []
        sslContext = ssl.create_default_context()

        for entity in entityJsonList:
            uid = entity['uid']
            websiteURL = entity['URL']
            if not websiteURL.startswith('https'):
                continue  # Ignore non-https sites
            addressWithoutHttps = websiteURL[8:]

            with sslContext.wrap_socket(socket.socket(), server_hostname=addressWithoutHttps) as s:
                try:
                    s.connect((addressWithoutHttps, 443))
                    websiteCertificate = s.getpeercert()
                except socket.error:
                    # If there's an error connecting, move on.
                    continue

            # Subject Details
            streetAddr = None
            locality = None
            postalCode = None
            subjectCountry = None
            subjectSerial = None
            subjectName = None
            tentativeSubjectResults = []
            for subjectAttributeOuter in websiteCertificate['subject']:
                for subjectAttributeInner in subjectAttributeOuter:
                    subjectAttributeInnerKey = subjectAttributeInner[0]
                    subjectAttributeInnerValue = subjectAttributeInner[1]
                    if subjectAttributeInnerKey == 'commonName':
                        returnResults.append([{'Domain Name': subjectAttributeInnerValue,
                                               'Entity Type': 'Domain'},
                                              {uid: {'Resolution': 'Certificate Subject Common Name',
                                                     'Notes': ''}}])

                    elif subjectAttributeInnerKey == 'streetAddress':
                        streetAddr = subjectAttributeInnerValue
                    elif subjectAttributeInnerKey == 'countryName':
                        subjectCountry = subjectAttributeInnerValue
                    elif subjectAttributeInnerKey == 'postalCode':
                        postalCode = subjectAttributeInnerValue
                    elif subjectAttributeInnerKey == 'localityName':
                        locality = subjectAttributeInnerValue

                    elif subjectAttributeInnerKey == 'serialNumber':
                        subjectSerial = subjectAttributeInnerValue
                    elif subjectAttributeInnerKey == 'organizationName':
                        subjectName = subjectAttributeInnerValue

            subjectIndex = None
            if subjectName is not None:
                subjectIndex = len(returnResults)
                subjectNameJSON = {'Organization Name': subjectName,
                                   'Entity Type': 'Organization'}
                if subjectSerial is not None:
                    subjectNameJSON['Registration Number'] = subjectSerial
                tentativeSubjectResults.append([subjectNameJSON,
                                                {uid: {'Resolution': 'Certificate Subject Organization',
                                                       'Notes': ''}}])

            # If we only have the serial of the subject, use that as the subject entity representation.
            elif subjectSerial is not None:
                subjectIndex = len(returnResults)
                tentativeSubjectResults.append([{'Phrase': subjectSerial,
                                                 'Entity Type': 'Phrase'},
                                                {uid: {'Resolution': 'Certificate Subject Serial Number',
                                                       'Notes': ''}}])

            # If we have no company name and no serial, the certificate belongs to an unknown org.
            if subjectIndex is None:
                subjectIndex = len(returnResults)
                tentativeSubjectResults.append([{'Organization Name': 'Unknown Organization',
                                                 'Entity Type': 'Organization'},
                                                {uid: {'Resolution': 'Certificate Subject Organization',
                                                       'Notes': ''}}])

            # If we have an address, fill it in. If not, create separate entities for each element.
            if streetAddr is not None:
                streetAddressJSON = {'Street Address': streetAddr,
                                     'Entity Type': 'Address'}
                if subjectCountry is not None:
                    streetAddressJSON['Country'] = subjectCountry
                if postalCode is not None:
                    streetAddressJSON['Postal Code'] = postalCode
                if locality is not None:
                    streetAddressJSON['Locality'] = locality
                tentativeSubjectResults.append([streetAddressJSON,
                                                {subjectIndex: {'Resolution': 'Certificate Subject Address',
                                                                'Notes': ''}}])
            else:
                if subjectCountry is not None:
                    tentativeSubjectResults.append([{'Country Name': subjectCountry,
                                                     'Entity Type': 'Country'},
                                                    {subjectIndex: {'Resolution': 'Certificate Subject Country',
                                                                    'Notes': ''}}])
                if postalCode is not None:
                    tentativeSubjectResults.append([{'Phrase': postalCode,
                                                     'Entity Type': 'Phrase'},
                                                    {subjectIndex: {'Resolution': 'Certificate Subject Postal Code',
                                                                    'Notes': ''}}])
                if locality is not None:
                    tentativeSubjectResults.append([{'Phrase': locality,
                                                     'Entity Type': 'Phrase'},
                                                    {subjectIndex: {'Resolution': 'Certificate Subject Locality',
                                                                    'Notes': ''}}])
            if len(tentativeSubjectResults) > 1:
                # If we have more than just 'Unknown Organization' as a result for the subject, consider the output.
                #   Otherwise, no point in including it.
                returnResults += tentativeSubjectResults

            # Validity dates for the certificate
            returnResults.append([{'Date': websiteCertificate['notBefore'],
                                   'Entity Type': 'Date'},
                                  {uid: {'Resolution': 'Certificate Start Date',
                                         'Notes': ''}}])
            returnResults.append([{'Date': websiteCertificate['notAfter'],
                                   'Entity Type': 'Date'},
                                  {uid: {'Resolution': 'Certificate Expiry Date',
                                         'Notes': ''}}])

            # Domain names included in the certificate.
            try:
                for altNameAttribute in websiteCertificate['subjectAltName']:
                    returnResults.append([{'Domain Name': altNameAttribute[1],
                                           'Entity Type': 'Domain'},
                                          {uid: {'Resolution': 'Certificate Subject Alternate Name',
                                                 'Notes': ''}}])
            except KeyError:
                pass

            # OCSP URLs. Often just one.
            try:
                for ocsp in websiteCertificate['OCSP']:
                    returnResults.append([{'URL': ocsp,
                                           'Entity Type': 'Website'},
                                          {uid: {'Resolution': 'Certificate OCSP URL',
                                                 'Notes': ''}}])
            except KeyError:
                pass

            # CA Issuer URL
            try:
                for caIssuer in websiteCertificate['caIssuers']:
                    returnResults.append([{'URL': caIssuer,
                                           'Entity Type': 'Website'},
                                          {uid: {'Resolution': 'Certificate Authority Issuer URL',
                                                 'Notes': ''}}])
            except KeyError:
                pass

            # CRL URLs
            try:
                for crlDistributionPoint in websiteCertificate['crlDistributionPoints']:
                    returnResults.append([{'URL': crlDistributionPoint,
                                           'Entity Type': 'Website'},
                                          {uid: {'Resolution': 'Certificate Authority Revocation List URL',
                                                 'Notes': ''}}])
            except KeyError:
                pass

            # Issuer information
            orgName = None
            orgCommonName = None
            orgCountry = None
            orgPostal = None
            orgLocality = None
            orgStateOrProvince = None
            orgUnitName = None
            for issuerAttributeOuter in websiteCertificate['issuer']:
                for issuerAttributeInner in issuerAttributeOuter:
                    issuerAttributeInnerKey = issuerAttributeInner[0]
                    issuerAttributeInnerValue = issuerAttributeInner[1]
                    if issuerAttributeInnerKey == 'organizationName':
                        orgName = issuerAttributeInnerValue
                    elif issuerAttributeInnerKey == 'commonName':
                        orgCommonName = issuerAttributeInnerValue
                    elif issuerAttributeInnerKey == 'countryName':
                        orgCountry = issuerAttributeInnerValue
                    elif issuerAttributeInnerKey == 'postalCode':
                        orgPostal = issuerAttributeInnerValue
                    elif issuerAttributeInnerKey == 'localityName':
                        orgLocality = issuerAttributeInnerValue
                    elif issuerAttributeInnerKey == 'stateOrProvinceName':
                        orgStateOrProvince = issuerAttributeInnerValue
                    elif issuerAttributeInnerKey == 'orgUnitName':
                        orgUnitName = issuerAttributeInnerValue

            issuerIndex = None
            if orgName is not None:
                issuerIndex = len(returnResults)
                returnResults.append([{'Organization Name': orgName,
                                       'Entity Type': 'Organization'},
                                      {uid: {'Resolution': 'Certificate Issuer Organization',
                                             'Notes': ''}}])
            if orgCommonName is not None:
                if issuerIndex is not None:
                    parentEntity = issuerIndex
                else:
                    parentEntity = uid
                    issuerIndex = len(returnResults)
                returnResults.append([{'Phrase': orgCommonName,
                                       'Entity Type': 'Phrase'},
                                      {parentEntity: {'Resolution': 'Certificate Issuer Common Name',
                                                      'Notes': ''}}])
            if issuerIndex is None:
                issuerIndex = len(returnResults)
                returnResults.append([{'Organization Name': 'Unknown Issuer',
                                       'Entity Type': 'Organization'},
                                      {uid: {'Resolution': 'Certificate Issuer Name',
                                             'Notes': ''}}])
            if orgCountry is not None:
                returnResults.append([{'Country Name': orgCountry,
                                       'Entity Type': 'Country'},
                                      {issuerIndex: {'Resolution': 'Certificate Issuer Country',
                                                     'Notes': ''}}])
            if orgPostal is not None:
                returnResults.append([{'Phrase': orgPostal,
                                       'Entity Type': 'Phrase'},
                                      {issuerIndex: {'Resolution': 'Certificate Issuer Postal Code',
                                                     'Notes': ''}}])
            if orgLocality is not None:
                returnResults.append([{'Phrase': orgLocality,
                                       'Entity Type': 'Phrase'},
                                      {issuerIndex: {'Resolution': 'Certificate Issuer Locality',
                                                     'Notes': ''}}])
            if orgStateOrProvince is not None:
                returnResults.append([{'Phrase': orgStateOrProvince,
                                       'Entity Type': 'Phrase'},
                                      {issuerIndex: {'Resolution': 'Certificate Issuer State / Province',
                                                     'Notes': ''}}])
            if orgUnitName is not None:
                returnResults.append([{'Phrase': orgUnitName,
                                       'Entity Type': 'Phrase'},
                                      {issuerIndex: {'Resolution': 'Certificate Issuer Organizational Unit Name',
                                                     'Notes': ''}}])

            # Certificate info - serial number and certificate version.
            returnResults.append([{'Phrase': websiteCertificate['serialNumber'],
                                   'Entity Type': 'Phrase'},
                                  {uid: {'Resolution': 'Certificate Serial Number',
                                         'Notes': ''}}])

            returnResults.append([{'Phrase': 'Certificate Version: ' + str(websiteCertificate['version']),
                                   'Entity Type': 'Phrase'},
                                  {uid: {'Resolution': 'Certificate Version',
                                         'Notes': ''}}])

        return returnResults
