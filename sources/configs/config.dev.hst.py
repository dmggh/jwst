import os

observatory = 'hst'
install_dir='/home/jmiller/work/workspace_crds/CRDS_server/webserver'

#
# servertype is what type of web server the install script should
# set up for you.  options are:
#
#   django
#       configure to use the django development server - works anywhere
#
#   mod_python
#       configure to use apache with mod_python - works on etc-dev1 or
#       anywhere that we have the *correct* mod_python available
#
#   wsgi
#       configure to use apache with wsgi - not implemented yet
#
servertype = 'django'

#
# http_port is the port number that the web server should listen on. 
# This uses your UID so you don't conflict with other developers.  If you
# personally want to run two servers, put a number here.
port = 8000

#
# turn on debugging 
#
# This is copied into django debug settings.
# This is available to other parts of the system.
# 
debug = True

#
# what kind of database to use.  choices are:
#
#   sqlite
#       a local sqlite database in your install directory
#   pyetc1
#       the pyetc1 development database on mysql server on goldink
#   pyetc2
#       the pyetc2 development database on mysql server on goldink
#       This one is mostly reserved for the demo server.
#
# The mysql client library is currently hacked together and run off the central store.
#
dbtype='sqlite'
table_prefix = 'crds_'

#
# data_dir is the directory where data files relating to specific
# requests are stored.  data_dir contains more deeply nested directories
# for the various request_id's.
#

data_dir = install_dir+"/data"

import pwd
version_prefix=pwd.getpwuid(os.getuid())[0]

CRDS_URL = "http://localhost:" + str(port) + "/"

CRDS_REFERENCE_URL = CRDS_URL + "get/"
CRDS_MAPPING_URL   = CRDS_URL + "get/"
