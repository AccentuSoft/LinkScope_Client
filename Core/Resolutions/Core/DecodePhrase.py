class DecodePhrase:
    # A string that is treated as the name of this resolution.
    name = "Decode Phrase"

    # A string that describes this resolution.
    description = "Decode encoded phrases."

    # A set of entities that this resolution can be ran on.
    originTypes = {'Phrase'}

    # A set of entities that could be the result of this resolution.
    resultTypes = {'Phrase'}

    # A dictionary of properties for this resolution. The key is the property name,
    # the value is the property attributes. The type of input expected from the user is determined by the
    # variable type of the 'value' parameter.
    parameters = {'Encoding Type': {'description': 'Select the type of encoding that was applied to the data.',
                                    'type': 'SingleChoice',
                                    'value': {'Binary', 'Hexadecimal', 'Base64'}
                                    }}

    def resolution(self, entityJsonList, parameters):
        import base64
        returnResult = []

        for entity in entityJsonList:
            uid = entity['uid']

            if parameters['Encoded Type'] == 'Hexadecimal':
                text = entity[list(entity)[1]].strip()
                data = str(bytearray.fromhex(text).decode())
                returnResult.append([{'Phrase': data,
                                      'Entity Type': 'Phrase'},
                                     {uid: {'Resolution': 'Hexadecimal Phrase', 'Notes': ''}}])

            elif parameters['Encoded Type'] == 'Base64':
                text = entity[list(entity)[1]].strip()
                data = base64.b64decode(text).decode()
                returnResult.append([{'Phrase': str(data),
                                      'Entity Type': 'Phrase'},
                                     {uid: {'Resolution': 'Base 64 Decoded Phrase', 'Notes': ''}}])

            elif parameters['Encoded Type'] == 'Binary':
                text = entity[list(entity)[1]].replace(' ', '')
                if len(text) % 8 != 0:
                    return "Malformed format not in Octaves"

                ascii_string = ''
                for binaryIndex in range(0, len(text), 8):
                    ascii_string += chr(int(text[binaryIndex:binaryIndex + 8], 2))
                returnResult.append([{'Phrase': str(ascii_string),
                                      'Entity Type': 'Phrase'},
                                     {uid: {'Resolution': 'Binary Decoded Phrase', 'Notes': ''}}])

        return returnResult
