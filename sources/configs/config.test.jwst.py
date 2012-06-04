import os

observatory = 'jwst'

install_root = '/data1/crds/' + observatory
apachemod = "/data1/pyetc_third_party_4/lib/apache"
port = 4995
CRDS_URL = "http://etcbrady.stsci.edu:" + str(port)

install_dir = install_root + '/webserver'
ref_path = install_root + '/references'
map_path = install_root + '/mappings'

servertype = 'mod_python'

debug = True
dbtype='sqlite'
table_prefix = 'crds_' + observatory
data_dir = install_dir+"/data"

PYSYN_CDBS = ""

CRDS_REFERENCE_URL = CRDS_URL + "/get/" 
CRDS_MAPPING_URL   = CRDS_URL + "/get/" 

# List of directories where delivered files are linked
CRDS_DELIVERY_DIRS = [
    install_root + "/deliveries",
]

# Master directory for the catalog file associated with a delivery
CRDS_CATALOG_DIR = install_root + "/catalogs"

