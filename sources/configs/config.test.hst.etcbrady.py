import os

DEBUG=debug=True
DEBUG_EXTRAS=False

observatory = 'hst'
install_root = '/grp/crds/' + observatory
port = 4997
CRDS_URL = "http://etcbrady.stsci.edu:" + str(port) + "/"
CRDS_SERVER_IP = "130.167.209.28"

servertype = 'mod_wsgi'
apachemod = install_root + "/webserver/lib"

dbtype='mysql'

PYSYN_CDBS = ""

# These should be relatively static and go through Django
CRDS_REFERENCE_URL = CRDS_URL + "get/"
CRDS_MAPPING_URL   = CRDS_URL + "get/"

# These may get redirected to the archive or a static file server
CRDS_UNCHECKED_REFERENCE_URL = CRDS_URL + "unchecked_get/"
CRDS_UNCHECKED_MAPPING_URL   = CRDS_URL + "unchecked_get/"

# These are the file states which are available for download or rpc.
# XXX TODO restrict to archived or operational
CRDS_DISTRIBUTION_STATES = ["delivered","archived","operational"]

