from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
debug = DEBUG = False
DEBUG_EXTRAS = False

HOST = "iljwdmsbcrdsv1"
PROXY = "jwst-crds-b5it"
observatory = 'jwst'
server_usecase ="b5it"
CRDS_SERVER_IP = "130.167.252.144"
port = 8001

# This is a VM-related storage partition used as server space
install_root = '/crds/data1/' + HOST

# This is a Isilon storage /crds/jwst/production used as file space
storage_path = '/ifs/crds/' + observatory + '/' + server_usecase

servertype = 'mod_wsgi'
apachemod = install_root + "/lib"
dbtype = 'mysql'

PYSYN_CDBS = ""

# These are the file states which are available for download or rpc.
# XXX TODO restrict to archived or operational
CRDS_DISTRIBUTION_STATES =  [ "archived", "operational", "delivered", "submitted", "archiving"]

# The primary URL used by end-users which passes through a proxy which
# assigns more user-friendly URLs based on standard ports 443.
# Server backup restorate occurs on an alternate port

BACKUP_URL_SCHEME = False

if BACKUP_URL_SCHEME:
    port += 1  # need backup port elsewhere
    CRDS_URL = "https://" + HOST + ".stsci.edu:" + str(port) + "/"
else:
    CRDS_URL = "https://" + PROXY + ".stsci.edu/" 

# The base server provides HTTPS on a non-standard port with a URL
# not normally used by end-users and possibly inaccessible offsite.
# The direct URL bypasses the proxy.
CRDS_DIRECT_URL = "https://" + HOST + ".stsci.edu:" + str(port) + "/"

# These should be relatively static and go through Django
CRDS_REFERENCE_URL = CRDS_URL + "get/"
CRDS_MAPPING_URL   = CRDS_URL + "get/"

# These may get redirected to the archive or a static file server
CRDS_UNCHECKED_REFERENCE_URL = "https://iwjwdms4auiwebv.stsci.edu/portal_build5/Download/file/JWST/reference"
CRDS_UNCHECKED_MAPPING_URL   = "https://iwjwdms4auiwebv.stsci.edu/portal_build5/Download/file/JWST/reference"

FORCE_REMOTE_MODE = False

ARCHIVE_PARAMETER_SERVICE_URL = "https://iljwdmsbarcv.stsci.edu:8888/crds"
# ARCHIVE_PARAMETER_SERVICE_URL = "http://jwdmsdevvm4.stsci.edu:8888/crds"
