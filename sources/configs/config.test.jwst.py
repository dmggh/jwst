import os

observatory = "jwst"
install_dir='/data1/CRDS/CRDS_jwst/webserver'

servertype = 'mod_python'
apachemod = "/data1/pyetc_third_party_4/lib/apache"
port = 4995

debug = True
dbtype='sqlite'
table_prefix = 'crds_jwst'
data_dir = install_dir+"/data"

PYSYN_CDBS = ""

CRDS_URL = "http://etcbrady.stsci.edu:" + str(port)   # no trailing slash
CRDS_REFERENCE_URL = CRDS_URL + "/get/" 
CRDS_MAPPING_URL   = CRDS_URL + "/get/" 

# List of directories where delivered files are linked
CRDS_DELIVERY_DIRS = [
    "/data1/CRDS/jwst/deliveries",
]

# Master directory for the catalog file associated with a delivery
CRDS_CATALOG_DIR = "/data1/CRDS/jwst/catalogs"

