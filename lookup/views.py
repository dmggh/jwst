from jsonrpc import jsonrpc_method
from jsonrpc.exceptions import OtherError

import crds.rmap as rmap
import base64

@jsonrpc_method('get_best_refs(String, Object)')
def get_best_refs(request, context, header):
    return rmap.get_best_refs(context, header)

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
    filepath = ctx.locate.locate_mapping(mapping)
    return open(filepath).read()

@jsonrpc_method('get_mapping_url(String, String)')
def get_mapping_url(request, context, mapping):
    ctx = rmap.get_cached_mapping(context)
    return ctx.locate.mapping_url("http://" + request.get_host(), mapping)

@jsonrpc_method('get_reference_data(String, String)')
def get_reference_data(request, context, reference):
    ctx = rmap.get_cached_mapping(context)
    filepath = ctx.locate.locate_reference(reference)
    refdata = open(filepath).read()
    return base64.b64encode(refdata)

@jsonrpc_method('get_reference_url(String, String)')
def get_reference_url(request, context, reference):
    ctx = rmap.get_cached_mapping(context)
    return ctx.locate.reference_url("http://" + request.get_host(), reference)

#@jsonrpc_method('lookup.sayHello')
#def whats_the_time(request, name='Lester'):
#  return "Hello %s" % name

#@jsonrpc_method('lookup.gimmeThat', authenticated=True)
#def something_special(request, secret_data):
#  return {'sauce': ['authenticated', 'sauce']}
