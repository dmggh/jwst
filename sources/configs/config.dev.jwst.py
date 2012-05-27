import os

observatory = "jwst"
install_dir='/home/jmiller/work/workspace_crds/CRDS_Server/webserver'

servertype = 'django'
port = 8000

debug = True
dbtype='sqlite'
table_prefix = 'crds_jwst_'
data_dir = install_dir+"/data"

PYSYN_CDBS = ""

CRDS_URL = "http://localhost:" + str(port) 
CRDS_REFERENCE_URL = CRDS_URL + "/get/" 
CRDS_MAPPING_URL   = CRDS_URL + "/get/" 

# List of directories where delivered files are linked
CRDS_DELIVERY_DIRS = [
    "/home/jmiller/CRDS/jwst/deliveries",
]

# Master directory for the catalog file associated with a delivery
CRDS_CATALOG_DIR = "/home/jmiller/CRDS/jwst/catalogs"

