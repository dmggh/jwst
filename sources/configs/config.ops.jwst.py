debug = DEBUG = False
DEBUG_EXTRAS = False

HOST = "pljwstcrdsv1"
PROXY = "jwst-crds"
observatory = 'jwst'
server_usecase ="ops"
CRDS_SERVER_IP = "130.167.252.81"
port = 8001

# This is a VM-related storage partition used as server space
install_root = '/crds/data1/' + HOST

# This is a Isilon storage /crds/jwst/production used as file space
storage_path = '/ifs/crds/' + observatory + '/' + server_usecase

CATALOG_DB_USER = "crds"
CATALOG_DB_PFILE = "/crds/data1/database/crds.dat"
CATALOG_DB_DSN = "HarpoDadsopsRepDsn"
REFFILE_DB_DSN = "HarpoReffileOpsRepDsn"

CRDS_DIRECT_URL = "https://" + HOST + ".stsci.edu:" + str(port) + "/"
CRDS_URL = "https://" + PROXY + ".stsci.edu/"

servertype = 'mod_wsgi'
apachemod = install_root + "/lib"
dbtype = 'mysql'

PYSYN_CDBS = ""

# These should be relatively static and go through Django
CRDS_REFERENCE_URL = CRDS_URL + "get/"
CRDS_MAPPING_URL   = CRDS_URL + "get/"

# These may get redirected to the archive or a static file server
CRDS_UNCHECKED_REFERENCE_URL = CRDS_URL + "unchecked_get/references/hst/"
CRDS_UNCHECKED_MAPPING_URL   = CRDS_URL + "unchecked_get/mappings/hst/"

# These are the file states which are available for download or rpc.
# XXX TODO restrict to archived or operational
CRDS_DISTRIBUTION_STATES = ["delivered", "submitted", "archiving", "archived", "operational"]

