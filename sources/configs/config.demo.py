#
# This is a config file for a demo deployment of crds.

servertype = 'mod_python'

add_ldap_auth = True

port = 4997

PYSYN_CDBS = "/eng/ssb/pyetc/cdbs.19.2rc1"

debug = True

dbtype='sqlite'

data_dir = install_dir+"/data"

telescopes = [ 'hst' ]

install_dir='/home/jmiller/CRDS/CRDS_server/webserver'
CRDS_REFERENCE_URL = "ftp://ftp.stsci.edu/cdbs/"   # .e.g http://crds_refs.stsci.edu
CRDS_MAPPING_URL =   "http://localhost:8000"

