import os

DEBUG=True
DEBUG_EXTRAS=False

observatory = 'hst'
install_root = '/grp/crds/' + observatory
port = 4997
CRDS_URL = "http://etcbrady.stsci.edu:" + str(port)

install_dir= install_root + '/webserver'
ref_path= install_root + '/references'
map_path= install_root + '/mappings'

CRDS_DELIVERY_DIR = install_root + "/deliveries"

# List of directories where delivered files are linked
CRDS_DELIVERY_DIRS = [
        CRDS_DELIVERY_DIR,
]

# Master directory for the catalog file associated with a delivery
CRDS_CATALOG_DIR = install_root + "/catalogs"

# Dir the file upload hanlder stores temporary large uploaded files.
FILE_UPLOAD_TEMP_DIR = install_root + "/uploads"

servertype = 'mod_python'
apachemod = "/data1/pyetc_third_party_4/lib/apache"

debug = True
dbtype='mysql'
table_prefix = 'crds_' + observatory
data_dir = install_dir+"/data"

PYSYN_CDBS = ""

CRDS_REFERENCE_URL = CRDS_URL + "/get/" 
CRDS_MAPPING_URL   = CRDS_URL + "/get/" 

# These are the file states which are available for download or rpc.
# XXX TODO restrict to archived or operational
CRDS_DISTRIBUTION_STATES = ["delivered","archived","operational"]

