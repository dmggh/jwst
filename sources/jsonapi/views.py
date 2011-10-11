from jsonrpc import jsonrpc_method
from jsonrpc.exceptions import OtherError

import crds.server.interactive.models as imodels
import crds.server.config as config
import crds.rmap as rmap
import base64

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

#@jsonrpc_method('jsonapi.sayHello')
#def whats_the_time(request, name='Lester'):
#  return "Hello %s" % name

#@jsonrpc_method('jsonapi.gimmeThat', authenticated=True)
#def something_special(request, secret_data):
#  return {'sauce': ['authenticated', 'sauce']}
