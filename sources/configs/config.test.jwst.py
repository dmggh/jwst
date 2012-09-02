import os

DEBUG=True
DEBUG_EXTRAS=False

observatory = 'jwst'
install_root = '/grp/crds/' + observatory
port = 4995
CRDS_URL = "http://etcbrady.stsci.edu:" + str(port)

servertype = 'mod_python'
apachemod = "/data1/pyetc_third_party_4/lib/apache"

debug = True
dbtype='mysql'

PYSYN_CDBS = ""

CRDS_REFERENCE_URL = CRDS_URL + "/get/" 
CRDS_MAPPING_URL   = CRDS_URL + "/get/" 

# These are the file states which are available for download or rpc.
# XXX TODO restrict to archived or operational
CRDS_DISTRIBUTION_STATES = ["delivered","archived","operational"]

# inline the contents of generic_config.py
HERE = os.path.dirname(__file__) or "./"
execfile(HERE + "/generic_config.py")
