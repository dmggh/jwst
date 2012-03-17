#!/bin/csh
setenv PYTHONPATH /python/lib/python/crds/server:/thirdparty/lib/python:/python/lib/python::
setenv LD_LIBRARY_PATH /home/jmiller/normal/lib
unsetenv DJANGO_SETTINGS_MODULE PYSYN_CDBS CRDS_DJANGO_SERVER
setenv SERVER_PORT 
setenv PATH /python/bin:/home/jmiller/normal/bin:/home/jmiller/workspace_pyetc/pyetc/test_utilities/spidering/scripts:/usr/local/cuda/bin:/usr/local/bin:/usr/bin:/bin:/home/jmiller/bin:/home/jmiller/workspace_pyetc/pyetc/test_utilities/spidering/scripts:/usr/local/cuda/bin:/usr/local/bin:/usr/bin:/bin:/home/jmiller/bin:/usr/lib/qt-3.3/bin:/usr/local/bin:/usr/bin:/bin
