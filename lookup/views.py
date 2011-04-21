from jsonrpc import jsonrpc_method
from jsonrpc.exceptions import OtherError

import crds.hst.gentools.lookup as hst_lookup

@jsonrpc_method('get_best_refs(Object)')
def get_best_refs(request, header):
    return hst_lookup.get_best_refs(header)

#@jsonrpc_method('lookup.sayHello')
#def whats_the_time(request, name='Lester'):
#  return "Hello %s" % name

#@jsonrpc_method('lookup.gimmeThat', authenticated=True)
#def something_special(request, secret_data):
#  return {'sauce': ['authenticated', 'sauce']}
