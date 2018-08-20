#-*-python-*-

import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'crds_server.settings'

from django.core.wsgi import get_wsgi_application

import warnings

'''
def application(environ, start_response):
    status = '200 OK'
    output = 'Hello World!'

    response_headers = [('Content-type', 'text/plain'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]
'''

# warnings.filterwarnings("warn", category=DeprecationWarning)

try:
    application = get_wsgi_application()
except Exception as exc:
    sys.stderr.write("Error in CRDS wsgi handler: " + repr(exc) + " :: " + str(exc))
    raise

