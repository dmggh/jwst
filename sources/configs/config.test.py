import os

servertype = 'mod_python'
port = 4997

debug = True
dbtype='sqlite'
table_prefix = 'crds_'
data_dir = install_dir+"/data"

PYSYN_CDBS = "/eng/ssb/pyetc/cdbs.19.2rc1"

telescopes = [ 'hst' ]

install_dir='/home/jmiller/workspace_crds/CRDS_server/webserver'
CRDS_REFERENCE_URL = "ftp://ftp.stsci.edu/cdbs/"   # .e.g http://crds_refs.stsci.edu
CRDS_MAPPING_URL =   "http://localhost:8000"

