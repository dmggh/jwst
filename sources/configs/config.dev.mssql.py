# from builtins import str
install_dir='/home/jmiller/work/workspace_crds/CRDS_server/webserver'

DEBUG=True
DEBUG_EXTRAS=False

#
# This is a config file for developers running pyetc.
#
# If you do not create config.py yourself, the install script will copy
# this file and use it.
#
# If you want to modify these settings for your own use, copy this
# file to config.py and edit it, then run the install script at the
# top level of the source tree.
#

#
# This config attempts to determine as much as possible automatically.
# For production use, you would use static assignements for everything.
#
# Some of this config is used at install time and some is used at run
# time.  Installing is easy enough that you can just install again if
# you change anything.
#

import os

# WARNING: do not use os.getcwd() - the return value is different at
# install and run time

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
port = os.getuid()

if port < 1024 :
    port = port + 10000
    
port = 8000

#
# Where should we find our cdbs
PYSYN_CDBS = "/eng/ssb/pyetc/cdbs.19.2rc1"


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
dbtype='mssql'

#
# install_dir is the directory where the software should be installed.
# This should be an absolute path.
# Uncomment & edit the line if you want to specify this; don't forget
# to fix the indentation. What needs to go onto your PYTHONPATH is
# not "install_dir", it's "install_dir/python/lib/python".
#
#
# install_dir="/data1/sienkiew/arf"
# install_dir=os.getcwd() + "/webserver"

# if not defined,  install_dir is defined by the install script essentially
# as os.getcwd() + "/webserver" at the time of running ./install from trunk
# Note that os.getcwd() is not valid in the later context of running the server
# so install_dir needs to be fixed at install time.

#
#
# If the install script has to create the config.py to use by copying
# this file ( config.dev.py ), it will set a default install_dir at
# the top of the file.  You can override it here, or do nothing to
# get the default.
#

#
# data_dir is the directory where data files relating to specific
# requests are stored.  data_dir contains more deeply nested directories
# for the various request_id's.
#

data_dir = install_dir+"/data"

observatory = 'hst'

import pwd
version_prefix=pwd.getpwuid(os.getuid())[0]

CRDS_URL = "http://localhost:" + str(port) + "/"

CRDS_REFERENCE_URL = CRDS_URL + "get/"   # .e.g http://crds_refs.stsci.edu
CRDS_MAPPING_URL   = CRDS_URL + "get/" # .e.g http://crds_refs.stsci.edu
