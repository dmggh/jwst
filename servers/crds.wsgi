import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'crds.server.settings'

import django.core.handlers.wsgi

try:
	application = django.core.handlers.wsgi.WSGIHandler()
except Exception, exc:
       sys.stderr.write("Error in CRDS wsgi handler: " + repr(exc) + " :: " + str(exc))
       raise
