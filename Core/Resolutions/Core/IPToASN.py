class IPToASN:
    # A string that is treated as the name of this resolution.
    name = "Get ASN From IP"

    category = "Network Infrastructure"

    # A string that describes this resolution.
    description = "Get the Autonomous System Number that the selected IP Addresses belong to."

    # A set of entities that this resolution can be ran on.
    originTypes = {'IP Address'}

    # A set of entities that could be the result of this resolution.
    resultTypes = {'Autonomous System'}

    # A dictionary of properties for this resolution. The key is the property name,
    # the value is the property attributes. The type of input expected from the user is determined by the
    # variable type of the 'value' parameter.
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        from ipwhois.net import Net
        from ipwhois.asn import IPASN
        import pycountry

        returnResult = []

        for entity in entityJsonList:
            if entity['Entity Type'] == 'IP Address':
                uid = entity['uid']
                IP_add = entity[list(entity)[1]]
                net = Net(IP_add)
                obj = IPASN(net)
                results = obj.lookup()
                index_of_child = len(returnResult)
                countryCode = results['asn_country_code']
                country = pycountry.countries.get(alpha_2=countryCode).name
                returnResult.append([{'AS Number': "AS" + results['asn'],
                                      'ASN Cidr': results['asn_cidr'],
                                      'Date Created': results['asn_date'],
                                      'Entity Type': 'Autonomous System'},
                                     {uid: {'Resolution': 'Autonomous System of IP', 'Notes': ''}}])
                returnResult.append(
                    [{'Organization Name': results['asn_registry'], 'Entity Type': 'Organization'},
                     {index_of_child: {'Resolution': 'ASN Registry', 'Notes': ''}}])
                returnResult.append(
                    [{'Country Name': country, 'Entity Type': 'Country'},
                     {index_of_child: {'Resolution': 'Country of Registry for ASN', 'Notes': ''}}])
                returnResult.append(
                    [{'Phrase': results['asn_description'], 'Entity Type': 'Phrase'},
                     {index_of_child: {'Resolution': 'ASN Description', 'Notes': ''}}])

        return returnResult
