import os.path
import base64

from jsonrpc import jsonrpc_method
from jsonrpc.exceptions import Error

import crds.server.interactive.models as imodels
import crds.server.config as config
import crds.rmap as rmap

# =============================================================================

from jsonrpc._json import dumps
from jsonrpc.site import jsonrpc_site

def get_jsonrpc_template_vars():
    """Return the dictionary of template variables required to instantiate
    the django-json-rpc Javascript template code.   Presently this info is used
    by the browser side code of the "interactive" app to define jsonrpc
    proxy objects which can be called like local Javascript functions.
    """
    desc = jsonrpc_site.service_desc()
    return {
            'methods': desc['procs'],
            'method_names_str': dumps([m['name'] for m in desc['procs']])
    }

# ===========================================================================

def get_url(observatory, filename):
    if rmap.is_mapping(filename):
        url = config.CRDS_MAPPING_URL + "/" + filename
    else:
        url = config.CRDS_REFERENCE_URL + "/" + filename
    return url

# ===========================================================================

class UnknownContextError(Error):
    """The specified context is not a known CRDS mapping."""
    
class UnknownMappingError(Error):
    """The specified mapping parameter is not a known CRDS mapping file."""
    
class UnknownReferenceError(Error):
    """The specified reference parameter is not a known CRDS reference file."""
    
class InvalidHeaderError(Error):
    """The specified header parameter is not suitable."""

def check_context(context):
    if not imodels.file_exists(context) or not rmap.is_mapping(context):
        raise UnknownContextError("Context parameter '%s' is not a known CRDS mapping file." % context)
    
def check_mapping(mapping):
    if not imodels.file_exists(mapping) or not rmap.is_mapping(mapping):
        raise UnknownMappingError("Mapping parameter '%s' is not a known CRDS mapping file." % mapping)
    
def check_reference(reference):
    blob = imodels.file_exists(reference)
    if not blob or not blob.type == "reference":
        raise UnknownReferenceError("Reference parameter '%s' is not a known CRDS reference file." % reference)
    
def check_header(header):
    if not isinstance(header, dict):
        raise InvalidHeaderError("Header parameter is not a dictionary.")
    for key, value in header.items():
        if not isinstance(key, (str, unicode)):
            raise InvalidHeaderError("Bad key in header... not a string.")
        if not isinstance(value, (str, unicode)):
            raise InvalidHeaderError("Bad value in header... not a string.")

# ===========================================================================

@jsonrpc_method('get_best_references(String, Object)')
def get_best_references(request, context, header):
    check_context(context)
    check_header(header)
    try:
        return rmap.get_best_references(context, header)
    except Exception, exc:
        raise Error("error in get_best_references " + str(exc))

@jsonrpc_method('get_mapping_names(String)')
def get_mapping_names(request, context):
    check_context(context)
    ctx = rmap.get_cached_mapping(context)
    return ctx.mapping_names()

@jsonrpc_method('get_reference_names(String)')
def get_reference_names(request, context):
    check_context(context)
    ctx = rmap.get_cached_mapping(context)
    return ctx.reference_names()

@jsonrpc_method('get_mapping_data(String, String)')
def get_mapping_data(request, context, mapping):
    check_context(context)
    check_mapping(mapping)
    where = rmap.locate_mapping(mapping)
    return open(where).read()

@jsonrpc_method('get_mapping_url(String, String)')
def get_mapping_url(request, context, mapping):
    check_context(context)
    check_mapping(mapping)
    ctx = rmap.get_cached_mapping(context)
    return get_url(ctx.observatory, mapping)

@jsonrpc_method('get_reference_data(String, String)')
def get_reference_data(request, context, reference):
    check_context(context)
    check_reference(reference)
    blob = imodels.FileBlob.load(reference)
    where = blob.pathname
    refdata = open(where).read()
    return base64.b64encode(refdata)

@jsonrpc_method('get_reference_url(String, String)')
def get_reference_url(request, context, reference):
    check_context(context)
    check_reference(reference)
    return get_url(ctx.observatory, reference)

@jsonrpc_method('file_exists(String)')
def file_exists(request, filename):
    return bool(imodels.file_exists(filename))
    
#@jsonrpc_method('jsonapi.sayHello')
#def whats_the_time(request, name='Lester'):
#  return "Hello %s" % name

#@jsonrpc_method('jsonapi.gimmeThat', authenticated=True)
#def something_special(request, secret_data):
#  return {'sauce': ['authenticated', 'sauce']}
