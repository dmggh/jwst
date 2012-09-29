install_dir= install_root + '/webserver'
ref_path= install_root + '/references'
map_path= install_root + '/mappings'

ref_path_full = install_root + "/references/" + observatory
map_path_full = install_root + "/mappings/" + observatory

CRDS_DELIVERY_DIR = install_root + "/deliveries"

# List of directories where delivered files are linked
CRDS_DELIVERY_DIRS = [
        CRDS_DELIVERY_DIR,
]

# Master directory for the catalog file associated with a delivery
CRDS_CATALOG_DIR = install_root + "/catalogs"

# Dir the file upload hanlder stores temporary large uploaded files.
FILE_UPLOAD_TEMP_DIR = install_root + "/uploads"

# Dir where deliverers can scp files for ingest.
CRDS_INGEST_DIR = install_root + "/ingest"

# table_prefix is added to the beginning of any database table name
table_prefix = 'crds_' + observatory

#
# data_dir is the directory where data files relating to specific
# requests are stored.  data_dir contains more deeply nested directories
# for the various request_id's.
#
data_dir = install_dir+"/data"

crds_server_dir = install_dir + "/python/lib/python/crds/server"

