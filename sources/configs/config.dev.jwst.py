# from builtins import str
debug = DEBUG = True
DEBUG_EXTRAS = False

HOST = "dljwcrds"
PROXY = "jwst-crds-dev"
observatory = 'jwst'
server_usecase = 'dev'
CRDS_SERVER_IP = "10.128.19.170"
port = 8001

# This is a VM-related storage partition used as server space
# install_root = '/crds/data1/' + HOST

# This is a Isilon storage /crds/hst/production used as file space
# storage_path = '/ifs/crds/' + observatory + '/' + server_usecase

CATALOG_DB_USER = "crds"
CATALOG_DB_PFILE = "/crds/data1/database/crds.dat"
CATALOG_DB_DSN = "HarpoDadsopsRepDsn"
REFFILE_DB_DSN = "HarpoReffileOpsRepDsn"

servertype = 'mod_wsgi'
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
CRDS_UNCHECKED_REFERENCE_URL = CRDS_URL + "unchecked_get/references/" + observatory + "/"
CRDS_UNCHECKED_MAPPING_URL   = CRDS_URL + "unchecked_get/mappings/" + observatory + "/"

FORCE_REMOTE_MODE = False

# ARCHIVE_PARAMETER_SERVICE_URL = "http://iljwdmsdarcv.stsci.edu:8888/crds"
# ARCHIVE_PARAMETER_SERVICE_URL = "https://dljwdms5v1.stsci.edu:8888/crds"
# ARCHIVE_PARAMETER_SERVICE_URL = "http://jwdmsdevvm4.stsci.edu:8888/crds"

CRDS_MOCK_ARCHIVE_PARAMETERS = "jwst-b7.2-iljwdmscarc1-2018-11-12.json"
# ARCHIVE_PARAMETER_SERVICE_URL = "http://iljwdmsbarcv1.stsci.edu:8888/crds"

# ARCHIVE_PARAMETER_SERVICE_URL = "http://dljwdmsv2.stsci.edu:8888/crds"

CRDS_STATUS_TO_ADDRESSES = ["jmiller@stsci.edu"]
CRDS_STATUS_CONFIRM_ADDRESSES  = ["jmiller@stsci.edu"]

