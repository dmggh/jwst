# from builtins import str
debug = DEBUG = False
DEBUG_EXTRAS = False

HOST = "plhstcrds"
PROXY = "hst-crds"
observatory = 'hst'
server_usecase ="ops"
CRDS_SERVER_IP = "10.128.19.61"
port = 8001

# This is a VM-related storage partition used as server space
# install_root = '/crds/data1/' + HOST

# This is a Isilon storage /crds/hst/production used as file space
# storage_path = '/ifs/crds/' + observatory + '/' + server_usecase

# CATALOG_DB_USER = "crds"
# CATALOG_DB_KEYTAB = "/crds/data1/database/crds_krb5.keytab"
# CATALOG_DB_DSN = "GROUCHOAG"   # availability group
# CATALOG_DB_DSN = "GROUCHO"   # original  test server
# CATALOG_DB_NAME = "dadsops_rep"   # or dadstest2

CATALOG_DB_USER = "crds"
CATALOG_DB_KEYTAB = "/crds/data1/database/crds_krb5.keytab"
CATALOG_DB_DSN = "HARPO"            # replicated OPS server
CATALOG_DB_NAME = "dadsops_rep"

servertype = 'mod_wsgi'
dbtype = 'mysql'

PYSYN_CDBS = ""

# These are the file states which are available for download or rpc.
# XXX TODO restrict to archived or operational
CRDS_DISTRIBUTION_STATES =  [ "archived", "operational",] # "delivered", "submitted", "archiving"]

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

CRDS_STATUS_TO_ADDRESSES = ["crds-servers@stsci.edu", "redcat@stsci.edu"]

