#!/bin/csh
setenv PYTHONPATH /home/jmiller/work/workspace_crds/CRDS_server/hst/webserver/python/lib/python/crds/server:/home/jmiller/work/workspace_crds/CRDS_server/hst/webserver/thirdparty/lib/python:/home/jmiller/work/workspace_crds/CRDS_server/hst/webserver/python/lib/python:
setenv LD_LIBRARY_PATH /home/jmiller/work/workspace_crds/CRDS_server/hst/webserver/lib:/Users/jmiller/work/lib:/Users/jmiller/work/framework/lib:/sw/lib
unsetenv DJANGO_SETTINGS_MODULE PYSYN_CDBS CRDS_DJANGO_SERVER
setenv SERVER_PORT 8000
setenv PATH /home/jmiller/work/workspace_crds/CRDS_server/hst/webserver/python/bin:/home/jmiller/work/workspace_crds/CRDS_server/hst/webserver/bin:/Applications/Emacs.app/Contents/MacOS:/Users/jmiller/work/framework/bin:/Users/jmiller/Library/Frameworks/Python.framework/Versions/2.7/bin:/Users/jmiller/work/bin:/opt/subversion/bin:/Users/jmiller/bin:/sbin:/bin:/usr/sbin:/usr/bin:/usr/games:/opt/local/bin:/usr/local/pvm/pvm3/bin:/usr/local/pvm/pvm3/lib:/usr/X11R6/bin
setenv CRDS_INSTALL_DIR  /home/jmiller/work/workspace_crds/CRDS_server/hst/webserver
setenv CRD_SERVER_URL  http://localhost:8000/
setenv CRDS_MAPPATH  /home/jmiller/work/workspace_crds/CRDS_server/hst/webserver/python/lib/python/crds/mappings
setenv CRDS_REFPATH  /home/jmiller/work/workspace_crds/CRDS_server/hst/references
setenv CRDS_CATALOG_DIR /home/jmiller/work/workspace_crds/CRDS_server/hst/catalogs
setenv DJANGO_SETTINGS_MODULE crds.server.settings
# we are runnning in the context of the django test server
setenv PYSYN_CDBS /eng/ssb/pyetc/cdbs.19.1rc3
setenv CRDS_DJANGO_SERVER 1
