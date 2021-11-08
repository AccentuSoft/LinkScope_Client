class ASNToCIDR:
    # A string that is treated as the name of this resolution.
    name = "Get CIDR from ASN"

    # A string that describes this resolution.
    description = "ASN to CIDR"

    # A set of entities that this resolution can be ran on.
    originTypes = {'Autonomous System'}

    # A set of entities that could be the result of this resolution.
    resultTypes = {'Network'}

    # A dictionary of properties for this resolution. The key is the property name,
    # the value is the property attributes. The type of input expected from the user is determined by the
    # variable type of the 'value' parameter.
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        from ipwhois.net import Net
        from ipwhois.asn import ASNOrigin

        returnResult = []

        for entity in entityJsonList:
            if entity['Entity Type'] == 'Autonomous System':
                ipWithPrefix = entity[list(entity)[2]]
                uid = entity['uid']
                split_string = ipWithPrefix.split("/", 1)
                ipWithOutPrefix = split_string[0]
                ASN = entity["AS Number"]
                try:
                    net = Net(ipWithOutPrefix)
                except Exception:
                    net = Net('1.1.1.1')
                obj = ASNOrigin(net)
                results = obj.lookup(asn=ASN)

                for network in results['nets']:
                    cidrWithPrefix = network['cidr']
                    split_string = cidrWithPrefix.split("/", 1)
                    cidrWithOutPrefix = split_string[0]
                    prefix = split_string[1]
                    index_of_child = len(returnResult)
                    returnResult.append([{'IP Address': cidrWithOutPrefix,
                                          'Range': prefix,
                                          'Entity Type': 'Network'},
                                         {uid: {'Resolution': 'ASN to CIDR', 'Notes': ''}}])
                    returnResult.append(
                        [{'Phrase': network['description'], 'Entity Type': 'Phrase'},
                         {index_of_child: {'Resolution': 'CIDR Description', 'Notes': ''}}])
                    returnResult.append(
                        [{'Organization Name': network['source'], 'Entity Type': 'Organization'},
                         {index_of_child: {'Resolution': 'ASN Registry', 'Notes': ''}}])
                    returnResult.append(
                        [{'Company Name': network['maintainer'], 'Entity Type': 'Company'},
                         {index_of_child: {'Resolution': 'Company Name', 'Notes': ''}}])

        return returnResult
