"""
This module defines base classes for implementing arbitrary REST-ful HTTP queries.
"""
import sys
import uuid
import json
import time
import os
import ssl

if sys.version_info < (3, 0, 0):
    import HTMLParser as parser_mod
    from urllib import urlencode
    from urllib2 import urlopen, Request
    # import html.parser as parser_mod
    # from urllib.parse import urlencode
    # from urllib.request import urlopen, Request
else:
    import html.parser as parser_mod
    from urllib.request import urlopen, Request

# =====================================================================

from crds.core import log, config, python23
from crds.client import proxy

from crds.core.exceptions import ServiceError

# =====================================================================

PARSER = parser_mod.HTMLParser()

# =====================================================================

class GetService(object):

    base_url = "abstract,  must subclass and define for actual service class."
    kind = "GET"

    def __init__(self, service_name):
        self.service_name = service_name
        self.service_url = self.base_url + "/" + service_name

    def __call__(self, **named_parameters):
        log.verbose(self.kind, repr(self.service_url), "with", repr(named_parameters))
        formatted_parameters = self.format_parameters(named_parameters)
        try:
            response = self.get_response(formatted_parameters)
        except Exception as exc:
            raise ServiceError("Network open failed calling service '{}' at '{}' : '{}'".format(
                    self.service_name, self.base_url, str(exc)))
        page = response.read()
        log.verbose("responded:", repr(page))
        result = self.get_and_decode_result(page)
        log.verbose("decoded:", repr(result))
        formatted = self.format_result(result)
        log.verbose("returning:", formatted)
        return formatted

    def get_response(self, param_str):
        url = self.service_url if not param_str else self.service_url + "?" + param_str
        return urlopen(url)

    def format_parameters(self, parameters):
        if isinstance(parameters, dict):
            parameters = list(parameters.items())
        formatted = "&".join([name + "="+ str(value) for (name, value) in parameters
                              if value is not None])
        return formatted

    def get_and_decode_result(self, page):
        decoded = page.decode("utf-8")
        result = json.loads(decoded)
        return result

    def format_result(self, result):
        return result

# =====================================================================

class PostService(GetService):

    kind = "POST"

    def get_response(self, formatted_parameters):    # full override
        headers = {
            "Content-type" : "application/json",
            }
        request = Request(self.service_url)
        request.add_header('Content-Type', 'application/json')
        return urlopen(request, formatted_parameters)

    def format_parameters(self, named_parameters):
        parameters = json.dumps(named_parameters)
        if not isinstance(parameters, bytes):  # Python-3
            parameters = parameters.encode("utf-8")
        return parameters

    def format_result(self, result):
        return result

