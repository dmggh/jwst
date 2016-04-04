#! /bin/sh
export PYTHONPATH="/crds/data1/dljwstcrdsv1/python/lib/python/crds/server:/crds/data1/dljwstcrdsv1/python/lib/python"
export LD_LIBRARY_PATH="/crds/data1/dljwstcrdsv1/lib:/crds/data1/dljwstcrdsv1/crds_stacks/crds_17/lib"
unset DJANGO_SETTINGS_MODULE PYSYN_CDBS CRDS_DJANGO_SERVER
export SERVER_PORT="8001"
export PATH="/crds/data1/dljwstcrdsv1/python/bin:/crds/data1/dljwstcrdsv1/bin:/crds/data1/dljwstcrdsv1/CRDS_server/host:/crds/data1/dljwstcrdsv1/crds_stacks/crds_17/bin:/usr/kerberos/bin:/usr/local/bin:/bin:/usr/bin:/usr/X11R6/bin"
export CRDS_INSTALL_DIR="/crds/data1/dljwstcrdsv1"
export CRDS_SERVER_URL="https://jwst-crds-dev.stsci.edu/"
export CRDS_PATH="/ifs/crds/jwst/dev/file_cache"
export CRDS_SERVER_FILES="/ifs/crds/jwst/dev/server_files"
export DJANGO_SETTINGS_MODULE="crds.server.settings"
export OPENSSL_NO_DEFAULT_ZLIB="1"
