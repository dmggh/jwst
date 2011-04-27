import sys
import StringIO
import crds.hst.gentools.lookup as hst_lookup

sys.stdout = StringIO.StringIO()
from jsonrpc.proxy import ServiceProxy
sys.stdout = sys.__stdout__

URL = 'http://localhost:8000/json/'

hst_lookup.load_header_cache()

def test_sayHello():
    S = ServiceProxy(URL)
    print S.lookup.sayHello('Sam')

def test_get_best_refs(fname):
    S = ServiceProxy(URL)
    header = hst_lookup.get_header_union(fname)
    references = S.get_best_refs("hst.pmap", header)["result"]
    return references

if __name__ == "__main__":
    for fname in sys.argv[1:]:
        print "====> Best references for", repr(fname)
        print test_get_best_refs(fname)
