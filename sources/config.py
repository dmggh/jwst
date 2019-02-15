# XXXXXXXX Late imports below

import os

observatory = CRDS_PROJECT = os.environ["CRDS_PROJECT"]
server_usecase = CRDS_USECASE = os.environ["CRDS_USECASE"]

INGEST_HOST = "pldmsins1.stsci.edu"

CRDS_MOCK_ARCHIVE_PARAMETERS = None
ARCHIVE_PARAMETER_SERVICE_URL = "https://undefined-archive-parameter-service.stsci.edu"

# This is a VM-related storage partition used as server space
install_root = '/crds/data1/persistent_local'

CRDS_SECRETS = os.environ["CRDS_SECRETS"]
CRDS_BACKUPS = os.environ["CRDS_BACKUPS"]
CRDS_SERVER_SETUP = os.environ["CRDS_SERVER_SETUP"]  # root directory for Apache support files
CRDS_INSTALL_DIR = os.environ["CRDS_INSTALL_DIR"]  # location of crds_server package install

# Location of /static web files.
CRDS_STATIC_DIR = os.environ["CRDS_STATIC_DIR"]

# Dir where deliverers can scp files for ingest.  Requires absolute
# isilon path to work with command line file submissions.
CRDS_INGEST_DIR = os.environ["CRDS_INGEST_DIR"]

# This is Isilon storage used to store deliveries, uploads, and the file cache.   Logical location
# storage_path = '/crds/data1/server_isilon'
# Originally intended as abstract link above,  too many issues to be worth it, now identical to physical
storage_path = CRDS_IFS = os.environ["CRDS_IFS"]

# This is Isilon storage used to store deliveries, uploads, and the file cache.  Physical location
isilon_storage_path = CRDS_ISILON = os.environ["CRDS_ISILON"]

CRDS_SECRETS = os.environ["CRDS_SECRETS"]
CRDS_SERVER_IP = os.environ["CRDS_SERVER_IP"]

# from builtins import str
debug = DEBUG = CRDS_DEBUG = bool(int(os.environ["CRDS_DEBUG"]))
DEBUG_EXTRAS = CRDS_DEBUG_EXTRAS = bool(int(os.environ["CRDS_DEBUG_EXTRAS"]))

HOST = CRDS_SERVER = os.environ["CRDS_SERVER"]
if CRDS_USECASE != "ops":
    PROXY = CRDS_PROJECT + "-crds-" + CRDS_USECASE
else:
    PROXY = CRDS_PROJECT + "-crds"

port = CRDS_PORT = int(os.environ["CRDS_PORT"])
CRDS_BACKUP_MODE = int(os.environ["CRDS_BACKUP_MODE"])

# This is a VM-related storage partition used as server space
# install_root = '/crds/data1/' + HOST

servertype = 'mod_wsgi'
dbtype = 'mysql'

PYSYN_CDBS = ""

# This is a Isilon storage /crds/hst/production used as file space
# storage_path = '/ifs/crds/' + observatory + '/' + server_usecase


# Directory where reprocessing system maintains state and store results
CRDS_REPROCESSING = os.environ["CRDS_REPROCESSING"]

# Parameters for connecting to HST archive database for CRDS repro
CRDS_REPRO_DB_USER = os.environ["CRDS_REPRO_DB_USER"]
CRDS_REPRO_DB_KEYTAB = os.environ["CRDS_REPRO_DB_KEYTAB"]
CRDS_REPRO_DB_DSN = os.environ["CRDS_REPRO_DB_DSN"]
CRDS_REPRO_DB_NAME = os.environ["CRDS_REPRO_DB_NAME"]

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

CRDS_UNCHECKED_REFERENCE_URL = os.environ["CRDS_UNCHECKED_REFERENCE_URL"]
CRDS_UNCHECKED_MAPPING_URL = os.environ["CRDS_UNCHECKED_MAPPING_URL"]

FORCE_REMOTE_MODE = int(os.environ["CRDS_FORCE_REMOTE_MODE"])

# ARCHIVE_PARAMETER_SERVICE_URL = "http://iljwdmsdarcv.stsci.edu:8888/crds"
# ARCHIVE_PARAMETER_SERVICE_URL = "https://dljwdms5v1.stsci.edu:8888/crds"
# ARCHIVE_PARAMETER_SERVICE_URL = "http://jwdmsdevvm4.stsci.edu:8888/crds"

# ARCHIVE_PARAMETER_SERVICE_URL = "http://iljwdmsbarcv1.stsci.edu:8888/crds"

# ARCHIVE_PARAMETER_SERVICE_URL = "http://dljwdmsv2.stsci.edu:8888/crds"

# Path to mock CRDS repro parameters,  if any
CRDS_MOCK_ARCHIVE_PARAMETERS = os.environ.get("CRDS_MOCK_ARCHIVE_PARAMETERS", None)

CRDS_SERVER_LOGS = os.environ["CRDS_SERVER_LOGS"]
CRDS_CRON_LOGS = os.environ["CRDS_CRON_LOGS"]

CRDS_STATUS_FROM_ADDRESS = "crds-servers@stsci.edu"
# CRDS_STATUS_TO_ADDRESSES = ["crds-servers@stsci.edu"]
# CRDS_STATUS_CONFIRM_ADDRESSES =  ["crds-servers@stsci.edu", "crds_datamng@stsci.edu"]

CRDS_STATUS_TO_ADDRESSES = os.environ["CRDS_STATUS_TO_ADDRESSES"].split(",")
CRDS_STATUS_CONFIRM_ADDRESSES  = os.environ["CRDS_STATUS_CONFIRM_ADDRESSES"].split(",")

# install_dir is the server installation location,  with the exceptions of logs
# this should be kept small.
install_dir = os.environ["CRDS_STACK"]

# CRDS_PATH is a crds cache created by the CRDS server.   Initially it is laid 
# out with the same structure as a cache created by crds.sync but this is not strictly
# enforced.  Testing with jsonapi populates it further as a normal cache.
# possibly multi-terabyte if complete and not linked to other storage
CRDS_PATH = os.environ["CRDS_PATH"]

# server_files is where server upload and delivery related files are kept
# possibly hundreds of gigabytes
server_files = CRDS_SERVER_FILES = os.environ["CRDS_SERVER_FILES"]

ref_path= CRDS_PATH + '/references'
map_path= CRDS_PATH + '/mappings'
ref_path_full = ref_path + "/" + observatory
map_path_full = map_path + "/" + observatory

# Where files are linked for pickup by DMS / archive.
CRDS_DELIVERY_DIR = os.environ["CRDS_DELIVERY_DIR"]

# List of directories where delivered files are linked
CRDS_DELIVERY_DIRS = [
        CRDS_DELIVERY_DIR,
]

# Master directory for the catalog file associated with a delivery
# CRDS keeps these even when OPUS/DMS/CDDS-pipeline is done archiving.
CRDS_CATALOG_DIR = os.environ["CRDS_CATALOG_DIR"]

# Dir the file upload hanlder stores temporary large uploaded files.
FILE_UPLOAD_TEMP_DIR = CRDS_UPLOADS_DIR = os.environ["CRDS_UPLOADS_DIR"]

# table_prefix is added to the beginning of any database table name
table_prefix = 'crds_' + observatory

#
# data_dir is the directory where data files relating to specific
# requests are stored.  data_dir contains more deeply nested directories
# for the various request_id's.   this is legacy from pyetc and minimally
# used or unused.
data_dir = install_dir+"/data"

crds_server_log_dir = CRDS_SERVER_LOGS = os.environ["CRDS_SERVER_LOGS"]

import crds_server
crds_server_dir = os.path.abspath(os.path.dirname(crds_server.__file__))

# Max size in bytes of interactive tar-balls,  intended for mapping bundles.
MAX_ARCHIVE_SIZE = 10**7   # ~10M,  current full hst archive is ~100k.



