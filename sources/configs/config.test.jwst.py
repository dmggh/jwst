import os

observatory = "jwst"
install_dir='/data1/CRDS/CRDS_jwst/webserver'

servertype = 'mod_python'
apachemod = "/data1/pyetc_third_party_4/lib/apache"
port = 4995

debug = True
dbtype='sqlite'
table_prefix = 'crds_jwst_'
data_dir = install_dir+"/data"

PYSYN_CDBS = ""

CRDS_URL = "http://etcbrady.stsci.edu:" + str(port)   # no trailing slash
CRDS_REFERENCE_URL = CRDS_URL + "/get/" 
CRDS_MAPPING_URL   = CRDS_URL + "/get/" 
