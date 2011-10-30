import os.path
import base64

from jsonrpc import jsonrpc_method
from jsonrpc.exceptions import OtherError

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
        url = mapping_url(filename)
    else:
        url = reference_url(filename)
    return url

def reference_url(reference):
    """Return a file URL which can be used to retrieve the specified `reference`.
    """
    reference = os.path.basename(reference)
    blob = imodels.FileBlob.load(reference)
    return config.CRDS_REFERENCE_URL + "/references/" + blob.observatory + \
        "/" + reference

def mapping_url(mapping):
    """Return a file URL which can be used to retrieve the specified `mapping`.
    """
    mapping = os.path.basename(mapping)
    blob = imodels.FileBlob.load(mapping)
    return config.CRDS_MAPPING_URL + "/mappings/" + blob.observatory + \
        "/" + mapping

# ===========================================================================


@jsonrpc_method('get_best_references(String, Object)')
def get_best_references(request, context, header):
    return rmap.get_best_references(context, header)

@jsonrpc_method('get_mapping_names(String)')
def get_mapping_names(request, context):
    ctx = rmap.get_cached_mapping(context)
    return ctx.mapping_names()

@jsonrpc_method('get_reference_names(String)')
def get_reference_names(request, context):
    ctx = rmap.get_cached_mapping(context)
    return ctx.reference_names()

@jsonrpc_method('get_mapping_data(String, String)')
def get_mapping_data(request, context, mapping):
    ctx = rmap.get_cached_mapping(context)
    where = rmap.locate_mapping(mapping)
    return open(where).read()

@jsonrpc_method('get_mapping_url(String, String)')
def get_mapping_url(request, context, mapping):
    ctx = rmap.get_cached_mapping(context)
    return rmap.mapping_url(config.CRDS_MAPPING_URL, mapping)

@jsonrpc_method('get_reference_data(String, String)')
def get_reference_data(request, context, reference):
    ctx = rmap.get_cached_mapping(context)
    blob = imodels.FileBlob.load(reference)
    where = blob.pathname
    refdata = open(where).read()
    return base64.b64encode(refdata)

@jsonrpc_method('get_reference_url(String, String)')
def get_reference_url(request, context, reference):
    ctx = rmap.get_cached_mapping(context)
    return ctx.locate.reference_url(config.CRDS_REFERENCE_URL, reference)

@jsonrpc_method('file_exists(String)')
def file_exists(request, filename):
    return imodels.file_exists(filename)
    
#@jsonrpc_method('jsonapi.sayHello')
#def whats_the_time(request, name='Lester'):
#  return "Hello %s" % name

#@jsonrpc_method('jsonapi.gimmeThat', authenticated=True)
#def something_special(request, secret_data):
#  return {'sauce': ['authenticated', 'sauce']}
