debug = DEBUG = True
DEBUG_EXTRAS = False

HOST = "tlhstcrdsv1"
observatory = 'jwst'
install_root = '/crds/data1/' + HOST
port = 8001
CRDS_URL = "http://" + HOST + ".stsci.edu:" + str(port) + "/"
CRDS_SERVER_IP = "130.167.252.67"

servertype = 'mod_wsgi'
apachemod = install_root + "/webserver/lib"
dbtype = 'mysql'

PYSYN_CDBS = ""

# These should be relatively static and go through Django
CRDS_REFERENCE_URL = CRDS_URL + "get/"
CRDS_MAPPING_URL   = CRDS_URL + "get/"

# These may get redirected to the archive or a static file server
CRDS_UNCHECKED_REFERENCE_URL = CRDS_URL + "unchecked_get/references/jwst/"
CRDS_UNCHECKED_MAPPING_URL   = CRDS_URL + "unchecked_get/mappings/jwst/"

# These are the file states which are available for download or rpc.
# XXX TODO restrict to archived or operational
CRDS_DISTRIBUTION_STATES = ["delivered", "archived", "operational"]

