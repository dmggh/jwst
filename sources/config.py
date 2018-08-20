from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
# XXXXXXXX Late imports below

from .site_config import observatory, server_usecase

CRDS_STATUS_FROM_ADDRESS = "crds-servers@stsci.edu"

INGEST_HOST = "pldmsins1.stsci.edu"

CRDS_MOCK_ARCHIVE_PARAMETERS = None
ARCHIVE_PARAMETER_SERVICE_URL = "https://undefined-archive-parameter-service.stsci.edu"

CRDS_STATUS_TO_ADDRESSES = ["crds-servers@stsci.edu"]
CRDS_STATUS_CONFIRM_ADDRESSES =  ["crds-servers@stsci.edu", "crds_datamng@stsci.edu"]

# This is a VM-related storage partition used as server space
install_root = '/crds/data1/server_local'

apachemod = install_root + "/lib"

# This is Isilon storage used to store deliveries, uploads, and the file cache.   Logical location
# storage_path = '/crds/data1/server_isilon'
# Originally intended as abstract link above,  too many issues to be worth it, now identical to physical
storage_path = '/ifs/crds/' + observatory + '/' + server_usecase

# This is Isilon storage used to store deliveries, uploads, and the file cache.  Physical location
isilon_storage_path = '/ifs/crds/' + observatory + '/' + server_usecase

# ^^^^^ -------------------------------------------------------------------------------------------
# vars above this line can be overridden in site_config.py copied from configs/config.xx.yy.py
# vvvvv -------------------------------------------------------------------------------------------
from .site_config import *

# install_dir is the server installation location,  with the exceptions of logs
# this should be kept small.
install_dir= install_root

# CRDS_PATH is a crds cache created by the CRDS server.   Initially it is laid 
# out with the same structure as a cache created by crds.sync but this is not strictly
# enforced.  Testing with jsonapi populates it further as a normal cache.
# possibly multi-terabyte if complete and not linked to other storage
CRDS_PATH = isilon_storage_path + "/file_cache"

# server_files is where server upload and delivery related files are kept
# possibly hundreds of gigabytes
server_files = isilon_storage_path + "/server_files"

ref_path= CRDS_PATH + '/references'
map_path= CRDS_PATH + '/mappings'
ref_path_full = ref_path + "/" + observatory
map_path_full = map_path + "/" + observatory

# Where files are linked for pickup by DMS / archive.
CRDS_DELIVERY_DIR = server_files + "/deliveries"

# List of directories where delivered files are linked
CRDS_DELIVERY_DIRS = [
        CRDS_DELIVERY_DIR,
]

# Master directory for the catalog file associated with a delivery
# CRDS keeps these even when OPUS/DMS/CDDS-pipeline is done archiving.
CRDS_CATALOG_DIR = server_files + "/catalogs"

# Dir the file upload hanlder stores temporary large uploaded files.
FILE_UPLOAD_TEMP_DIR = server_files + "/uploads"

# Dir where deliverers can scp files for ingest.  Requires absolute
# isilon path to work with command line file submissions.
CRDS_INGEST_DIR = isilon_storage_path + "/server_files/ingest"

# Dir where dynamic mapping bundles are kept.
CRDS_ARCHIVE_CACHE_DIR = server_files + "/archive_cache"

# table_prefix is added to the beginning of any database table name
table_prefix = 'crds_' + observatory

#
# data_dir is the directory where data files relating to specific
# requests are stored.  data_dir contains more deeply nested directories
# for the various request_id's.   this is legacy from pyetc and minimally
# used or unused.
data_dir = install_dir+"/data"

crds_server_log_dir = install_dir + "/server/logs"
crds_server_dir = install_dir + "/python/lib/python/crds_server"

# Max size in bytes of interactive tar-balls,  intended for mapping bundles.
MAX_ARCHIVE_SIZE = 10**7   # ~10M,  current full hst archive is ~100k.



