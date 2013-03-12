import os

DEBUG=True
DEBUG_EXTRAS=False

observatory = 'jwst'
install_root = '/grp/crds/' + observatory
port = 4995
CRDS_URL = "http://etcbrady.stsci.edu:" + str(port) + "/"

servertype = 'mod_wsgi'
apachemod = install_root + "/webserver/lib"

debug = True
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

