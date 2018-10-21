# from builtins import str
debug = DEBUG = True
DEBUG_EXTRAS = False

HOST = "iljwdmsccrds"
PROXY = "jwst-crds-cit"
observatory = 'jwst'
server_usecase ="cit"
CRDS_SERVER_IP = "10.128.19.148"
port = 8001

# This is a VM-related storage partition used as server space
# install_root = '/crds/data1/' + HOST

# This is a Isilon storage /crds/jwst/production used as file space
# storage_path = '/ifs/crds/' + observatory + '/' + server_usecase

servertype = 'mod_wsgi'
dbtype = 'mysql'

PYSYN_CDBS = ""

# These are the file states which are available for download or rpc.
# XXX TODO restrict to archived or operational
CRDS_DISTRIBUTION_STATES =  [ "archived", "operational"] # "delivered", "submitted", "archiving"]

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

CRDS_UNCHECKED_REFERENCE_URL = CRDS_URL + "unchecked_get/references/" + observatory + "/"
CRDS_UNCHECKED_MAPPING_URL   = CRDS_URL + "unchecked_get/mappings/" + observatory + "/"

# CRDS_UNCHECKED_REFERENCE_URL = "https://iwjwdmscauiweb.stsci.edu/portal/Download/file/JWST/reference/"
# CRDS_UNCHECKED_MAPPING_URL = "https://iwjwdmscauiweb.stsci.edu/portal/Download/file/JWST/reference/"

FORCE_REMOTE_MODE = False

# ARCHIVE_PARAMETER_SERVICE_URL = "https://undefined-archive-parameter-service.stsci.edu:8888/crds"
# CRDS_MOCK_ARCHIVE_PARAMETERS = "jwst-b7.1-cit-2017-06-17.json"

# ARCHIVE_PARAMETER_SERVICE_URL = "http://jwdmsdevvm4.stsci.edu:8888/crds"

# ARCHIVE_PARAMETER_SERVICE_URL = "https://undefined-archive-parameter-service.stsci.edu:8888/crds"
# CRDS_MOCK_ARCHIVE_PARAMETERS = "jwst-b7.1-iljwdmsbarcv1-2017-11-14.json"

ARCHIVE_PARAMETER_SERVICE_URL = "http://iljwdmscarc1.stsci.edu:8888/crds"
