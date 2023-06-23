#!/usr/bin/env python3


class DecodeRedirectUrlParameter:
    name = "Decode Redirect URL"
    category = "Website Information"
    description = "Search the URL's parameters to see where you'll be redirected."
    originTypes = {'Website'}
    resultTypes = {'Website'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        import contextlib
        from urllib.parse import urlparse
        from urllib.parse import parse_qs
        from urllib.parse import unquote
        from base64 import b64decode

        def get_redirect_value(parameter_arg: str) -> str:
            with contextlib.suppress(Exception):
                clean_val = unquote(parameter_arg)
                if urlparse(clean_val).scheme:
                    return clean_val
                clean_val = unquote(b64decode(parameter_arg).decode('UTF-8'))
                if urlparse(clean_val).scheme:
                    return clean_val
            return ''

        returnResults = []

        for entity in entityJsonList:
            primaryField = entity['URL'].strip()
            parsed_url = urlparse(primaryField, allow_fragments=False)

            parsed_url_params = parse_qs(parsed_url.query)
            for param, param_value in parsed_url_params.items():
                param_potential_url_value = get_redirect_value(', '.join(param_value))
                if param_potential_url_value:
                    parsed_url_params_copy = dict(parsed_url_params)
                    parsed_url_params_copy.pop(param)
                    new_entity = {'URL': param_potential_url_value,
                                  'Entity Type': 'Website'}
                    for param_copy, param_value_copy in parsed_url_params_copy.items():
                        new_entity[param_copy] = ', '.join(param_value_copy)
                    returnResults.append([new_entity,
                                          {entity['uid']: {'Resolution': 'Redirect To',
                                                           'Notes': ''}}])
                    break

        return returnResults
