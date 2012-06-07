import os

observatory = 'jwst'
port = 4995
CRDS_URL = "http://etcbrady.stsci.edu:" + str(port)
install_root = '/data1/crds/' + observatory

install_dir = install_root + '/webserver'
ref_path = install_root + '/references'
map_path = install_root + '/mappings'

CRDS_DELIVERY_DIR = install_root + "/deliveries"

# List of directories where delivered files are linked
CRDS_DELIVERY_DIRS = [
        CRDS_DELIVERY_DIR,
]

servertype = 'mod_python'
apachemod = "/data1/pyetc_third_party_4/lib/apache"

debug = True
dbtype='sqlite'
table_prefix = 'crds_' + observatory
data_dir = install_dir+"/data"

PYSYN_CDBS = ""

CRDS_REFERENCE_URL = CRDS_URL + "/get/" 
CRDS_MAPPING_URL   = CRDS_URL + "/get/" 

