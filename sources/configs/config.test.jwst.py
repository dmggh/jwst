debug = DEBUG = True
DEBUG_EXTRAS = False

HOST = "tljwstcrdsv1"
observatory = 'jwst'
server_usecase = 'test'
CRDS_SERVER_IP = "130.167.252.40"
port = 8001

# This is a VM-related storage partition used as server space
install_root = '/crds/data1/' + HOST

# This is a Isilon storage /crds/hst/production used as file space
storage_path = '/crds/' + observatory + '/' + server_usecase

# XXX PLACEHOLDERS, not valid for JWST
CATALOG_DB_USER = "crds"
CATALOG_DB_PFILE = "/crds/data1/database/crds.dat"
CATALOG_DB_DSN = "HarpoDadsopsRepDsn"
REFFILE_DB_DSN = "HarpoReffileOpsRepDsn"
# XXX PLACEHOLDERS, not valid for JWST

CRDS_URL = "http://" + HOST + ".stsci.edu:" + str(port) + "/"

servertype = 'mod_wsgi'
apachemod = install_root + "/lib"
dbtype = 'mysql'

PYSYN_CDBS = ""

# These should be relatively static and go through Django
CRDS_REFERENCE_URL = CRDS_URL + "get/"
CRDS_MAPPING_URL   = CRDS_URL + "get/"

# These may get redirected to the archive or a static file server
CRDS_UNCHECKED_REFERENCE_URL = CRDS_URL + "unchecked_get/references/" + observatory + "/"
CRDS_UNCHECKED_MAPPING_URL   = CRDS_URL + "unchecked_get/mappings/" + observatory + "/"

# These are the file states which are available for download or rpc.
# XXX TODO restrict to archived or operational
CRDS_DISTRIBUTION_STATES = ["delivered", "archived", "operational"]

