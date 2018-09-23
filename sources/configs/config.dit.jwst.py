# from builtins import str
debug = DEBUG = False
DEBUG_EXTRAS = False

HOST = "iljwdmsdcrdsv1"
PROXY = "jwst-crds-dit"
observatory = 'jwst'
server_usecase ="dit"
CRDS_SERVER_IP = "130.167.252.189"
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

# As of 2016-04-18:

# These may get redirected to the archive or a static file server
# CRDS_UNCHECKED_REFERENCE_URL = CRDS_URL + "unchecked_get/references/" + observatory + "/"
# CRDS_UNCHECKED_MAPPING_URL   = CRDS_URL + "unchecked_get/mappings/" + observatory + "/"

CRDS_UNCHECKED_REFERENCE_URL = "https://iwjwdmsdauiwebv.stsci.edu/portal/Download/file/JWST/reference/"
CRDS_UNCHECKED_MAPPING_URL = "https://iwjwdmsdauiwebv.stsci.edu/portal/Download/file/JWST/reference/"

FORCE_REMOTE_MODE = False

# From Kim Dupries,  likely B6 equivalents:
#
# https://iljwdmscarcv.stsci.edu:8888/crds
# https://dads6.stsci.edu:8888/crds
# https://dadsc.stsci.edu:8888/crds

ARCHIVE_PARAMETER_SERVICE_URL = "http://iljwdmsdarcv.stsci.edu:8888/crds"
# ARCHIVE_PARAMETER_SERVICE_URL = "https://jwdmsdevvm4:8888/crds"
# CRDS_MOCK_ARCHIVE_PARAMETERS = "jwst-b6-params.json"
