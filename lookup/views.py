from jsonrpc import jsonrpc_method
from jsonrpc.exceptions import OtherError

import crds.rmap as rmap

@jsonrpc_method('get_best_refs(String, Object)')
def get_best_refs(request, observatory, header):
    return rmap.get_best_refs(header, observatory)

#@jsonrpc_method('lookup.sayHello')
#def whats_the_time(request, name='Lester'):
#  return "Hello %s" % name

#@jsonrpc_method('lookup.gimmeThat', authenticated=True)
#def something_special(request, secret_data):
#  return {'sauce': ['authenticated', 'sauce']}
