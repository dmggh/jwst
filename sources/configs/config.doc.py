# This file lists all of the configuration options available to config.py

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
servertype = 'mod_python'

#
# if we are using the django server, do not run the second process that
# looks for changes to python files.  This makes it easier for scripts to
# kill the django server.
noreload=True

#
# If your servertype is mod_python, you can set add_ldap_auth=True to 
# make it authenticate from the institute LDAP server; this can be
# useful for testing, since only institute users have access.
#
add_ldap_auth = True

#
# http_port is the port number that the web server should listen on. 
# This uses your UID so you don't conflict with other developers.  If you
# personally want to run two servers, put a number here.
port = 4000

#
# Where should we find our cdbs

# This is where Vicki has provided a correct and stable CDBS for us
PYSYN_CDBS = "/eng/ssb/syn_pysyn/cdbs_pinned"

#
# turn on debugging 
#
# This is copied into django debug settings.
# This is available to other parts of the system.
# 
debug = False

#
# what kind of database to use.  choices are:
#
#   sqlite
#       sqlite database in a local file
#
#   pyetc1
#   pyetc2
#       mysql databases on goldink
#
dbtype='pyetc2'

#
# install_dir is the directory where the software should be installed.
# This should be an absolute path.
#
# install_dir="/data1/sienkiew/arf"
#
# If you do not set install_dir here, the install script will add one.

#
# data_dir is the directory where data files relating to specific
# requests are stored.  data_dir contains more deeply nested directories
# for the various request_id's.
#

data_dir = install_dir+"/data"

#
# table_prefix is an optional prefix that django will attach to the
# database table names.  If you set this, the table will be named
#   table_prefix + '_etcrequest'
# instead of
#   'etc_etcrequest'
#
# By using different table_prefix values, you can have multiple pyetc
# instances use the same database without seeing each other.
#
table_prefix = 'instance1'


#
# version_prefix (if present) is a string to put on front of the short
# version number.
version_prefix = 'config.doc.'

observatory = 'hst'

install_dir='/home/jmiller/CRDS/CRDS_server/webserver'
CRDS_REFERENCE_URL = "ftp://ftp.stsci.edu/cdbs/"   # .e.g http://crds_refs.stsci.edu
CRDS_MAPPING_URL =   "http://etcbrady.stsci.edu:8000"

