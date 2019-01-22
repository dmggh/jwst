import os

CRDS_SECRETS = os.environ["CRDS_SECRETS"]
CRDS_SERVER_IP = os.environ["CRDS_SERVER_IP"]

# from builtins import str
debug = DEBUG = CRDS_DEBUG = bool(int(os.environ["CRDS_DEBUG"]))
DEBUG_EXTRAS = CRDS_DEBUG_EXTRAS = bool(int(os.environ["CRDS_DEBUG_EXTRAS"]))

HOST = CRDS_SERVER = os.environ["CRDS_SERVER"]
observatory = CRDS_PROJECT = os.environ["CRDS_PROJECT"]
server_usecase = CRDS_USECASE = os.environ["CRDS_USECASE"]

if CRDS_USECASE != "ops":
    PROXY = observatory + "-crds-" + CRDS_USECASE
else:
    PROXY = observatory + "-crds"

port = CRDS_PORT = int(os.environ["CRDS_PORT"])
CRDS_BACKUP_MODE = int(os.environ["CRDS_BACKUP_MODE"])

# This is a VM-related storage partition used as server space
# install_root = '/crds/data1/' + HOST

# This is a Isilon storage /crds/hst/production used as file space
# storage_path = '/ifs/crds/' + observatory + '/' + server_usecase

CATALOG_DB_USER = "crds"
CATALOG_DB_PFILE = f"${CRDS_SECRETS}/crds.dat"
CATALOG_DB_DSN = "HarpoDadsopsRepDsn"
REFFILE_DB_DSN = "HarpoReffileOpsRepDsn"

servertype = 'mod_wsgi'
dbtype = 'mysql'

PYSYN_CDBS = ""

# These are the file states which are available for download or rpc.
# XXX TODO restrict to archived or operational
CRDS_DISTRIBUTION_STATES = os.environ["CRDS_DISTRIBUTION_STATES"].split(",")

# The primary URL used by end-users which passes through a proxy which
# assigns more user-friendly URLs based on standard ports 443.
# Server backup restorate occurs on an alternate port
if CRDS_BACKUP_MODE:
    CRDS_URL = "https://" + HOST + ".stsci.edu:" + str(CRDS_PORT) + "/"
else:
    CRDS_URL = "https://" + PROXY + ".stsci.edu/" 

# The base server provides HTTPS on a non-standard port with a URL
# not normally used by end-users and possibly inaccessible offsite.
# The direct URL bypasses the proxy.
CRDS_DIRECT_URL = "https://" + HOST + ".stsci.edu:" + str(CRDS_PORT) + "/"

# These should be relatively static and go through Django
CRDS_REFERENCE_URL = CRDS_URL + "get/"
CRDS_MAPPING_URL   = CRDS_URL + "get/"

# These may get redirected to the archive or a static file server
CRDS_UNCHECKED_REFERENCE_URL = CRDS_URL + "unchecked_get/references/" + observatory + "/"
CRDS_UNCHECKED_MAPPING_URL   = CRDS_URL + "unchecked_get/mappings/" + observatory + "/"

FORCE_REMOTE_MODE = int(os.environ["CRDS_FORCE_REMOTE_MODE"])

# ARCHIVE_PARAMETER_SERVICE_URL = "http://iljwdmsdarcv.stsci.edu:8888/crds"
# ARCHIVE_PARAMETER_SERVICE_URL = "https://dljwdms5v1.stsci.edu:8888/crds"
# ARCHIVE_PARAMETER_SERVICE_URL = "http://jwdmsdevvm4.stsci.edu:8888/crds"

# ARCHIVE_PARAMETER_SERVICE_URL = "http://iljwdmsbarcv1.stsci.edu:8888/crds"

# ARCHIVE_PARAMETER_SERVICE_URL = "http://dljwdmsv2.stsci.edu:8888/crds"

# Path to mock parameters file,  if any
CRDS_MOCK_ARCHIVE_PARAMETERS = os.environ.get("CRDS_MOCK_ARCHIVE_PARAMETERS", None)

CRDS_STATUS_TO_ADDRESSES = os.environ["CRDS_STATUS_TO_ADDRESSES"].split(",")
CRDS_STATUS_CONFIRM_ADDRESSES  = os.environ["CRDS_STATUS_CONFIRM_ADDRESSES"].split(",")

# Directory where reprocessing system maintains state and store results
CRDS_REPROCESSING = os.environ["CRDS_REPROCESSING"]

CRDS_SERVER_LOGS = os.environ["CRDS_SERVER_LOGS"]
CRDS_CRON_LOGS = os.environ["CRDS_CRON_LOGS"]

