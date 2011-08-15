import os

install_dir='/data1/CRDS/CRDS_server/webserver'

CRDS_REFERENCE_URL = "ftp://ftp.stsci.edu/cdbs/"   # .e.g http://crds_refs.stsci.edu
CRDS_MAPPING_URL =   "http://etcbrady.stsci.edu:4997"

servertype = 'mod_python'
apachemod = "/data1/pyetc_third_party_4/lib/apache"
port = 4997

debug = True
dbtype='sqlite'
table_prefix = 'crds_'
data_dir = install_dir+"/data"

PYSYN_CDBS = ""

telescopes = [ 'hst' ]

