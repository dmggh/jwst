from jsonrpc import jsonrpc_method
from jsonrpc.exceptions import OtherError

import crds.rmap as rmap

@jsonrpc_method('get_best_refs(String, Object)')
def get_best_refs(request, observatory, header):
    return rmap.get_best_refs(header, observatory)

@jsonrpc_method('get_mapping_names(String)')
def get_mapping_names(request, context):
    ctx = rmap.get_pipeline_context("hst", context)
    return ctx.mapping_names()

@jsonrpc_method('get_reference_names(String)')
def get_reference_names(request, context):
    ctx = rmap.get_pipeline_context("hst", context)
    return ctx.reference_names()

@jsonrpc_method('get_mapping_data(String, String)')
def get_mapping_data(request, context, mapping):
    ctx = rmap.get_pipeline_context("hst", context)
    filepath = ctx.locate_mapping(mapping)
    return open(filepath).read()

@jsonrpc_method('get_reference_data(String, String)')
def get_reference_data(request, context, reference):
    ctx = rmap.get_pipeline_context("hst", context)
    filepath = ctx.locate_reference(reference)
    return open(filepath).read()

#@jsonrpc_method('lookup.sayHello')
#def whats_the_time(request, name='Lester'):
#  return "Hello %s" % name

#@jsonrpc_method('lookup.gimmeThat', authenticated=True)
#def something_special(request, secret_data):
#  return {'sauce': ['authenticated', 'sauce']}
