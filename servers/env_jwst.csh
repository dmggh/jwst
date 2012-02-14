#!/bin/csh
setenv PYTHONPATH /data1/CRDS/CRDS_jwst/webserver/python/lib/python/crds/server:/data1/CRDS/CRDS_jwst/webserver/thirdparty/lib/python:/data1/CRDS/CRDS_jwst/webserver/python/lib/python/crds/server:/data1/CRDS/CRDS_jwst/webserver/thirdparty/lib/python:/data1/CRDS/CRDS_jwst/webserver/python/lib/python:/home/jmiller/CRDS/CRDS_jwst/webserver/thirdparty/lib/python:/home/jmiller/CRDS/CRDS_jwst/webserver/python/lib/python:/data1/pyetc_third_party_5/lib/python
setenv LD_LIBRARY_PATH /data1/pyetc_third_party_4/lib:/usr/stsci/Python-2.7.1/lib/
unsetenv DJANGO_SETTINGS_MODULE PYSYN_CDBS CRDS_DJANGO_SERVER
setenv SERVER_PORT 4995
setenv PATH /data1/CRDS/CRDS_jwst/webserver/python/bin:/data1/CRDS/CRDS_jwst/webserver/python/bin:/data1/pyetc_third_party_4/bin:/usr/stsci/Python-2.7.1/bin:/data2/iraf/pandokia/bin:/home/iraf/bin:/usr/kerberos/bin:/usr/local/bin:/bin:/usr/bin:/usr/X11R6/bin
# This file defines required environment variables for the CRDS client

# Where you want your CRDS mapping cache to be rooted.   Map files will
# be stored relative to this directory based on a scheme defined in the
# observatory package.  defaults to site-packages/crds/<observatory>
# setenv CRDS_MAPPATH /data1/CRDS/hst/mappings

# Where you want your CRDS reference cache to be rooted.   Reference files
# will be stored relative to this directory based on a scheme defined in the
# observatory package. defaults to site-packages/crds/<observatory>/references
# setenv CRDS_REFPATH /data1/CRDS/hst/references

# The URL for the CRDS server used by remote service calls,  
#    .e.g. http://etcbrady.stsci.edu:4995
setenv CRDS_SERVER_URL  http://etcbrady.stsci.edu:4995
setenv DJANGO_SETTINGS_MODULE crds.server.settings
setenv PYSYN_CDBS 
