#! /bin/csh
setenv PYTHONPATH /crds/data1/dljwstcrdsv1/python/lib/python/crds/server:/crds/data1/dljwstcrdsv1/python/lib/python
setenv LD_LIBRARY_PATH /crds/data1/dljwstcrdsv1/lib:/crds/data1/dljwstcrdsv1/crds_stacks/crds_17/lib
unsetenv DJANGO_SETTINGS_MODULE PYSYN_CDBS CRDS_DJANGO_SERVER
setenv SERVER_PORT 8001
setenv PATH /crds/data1/dljwstcrdsv1/python/bin:/crds/data1/dljwstcrdsv1/bin:/crds/data1/dljwstcrdsv1/CRDS_server/host:/crds/data1/dljwstcrdsv1/crds_stacks/crds_17/bin:/usr/kerberos/bin:/usr/local/bin:/bin:/usr/bin:/usr/X11R6/bin
setenv CRDS_INSTALL_DIR  /crds/data1/dljwstcrdsv1
setenv CRDS_SERVER_URL  https://jwst-crds-dev.stsci.edu/
setenv CRDS_PATH  /ifs/crds/jwst/dev/file_cache
setenv CRDS_SERVER_FILES  /ifs/crds/jwst/dev/server_files
setenv DJANGO_SETTINGS_MODULE crds.server.settings
setenv OPENSSL_NO_DEFAULT_ZLIB 1
