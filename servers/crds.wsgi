#-*-python-*-

import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'crds.server.settings'

from django.core.wsgi import get_wsgi_application

'''
def application(environ, start_response):
    status = '200 OK'
    output = 'Hello World!'

    response_headers = [('Content-type', 'text/plain'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]
'''

try:
    application = get_wsgi_application()
except Exception, exc:
    sys.stderr.write("Error in CRDS wsgi handler: " + repr(exc) + " :: " + str(exc))
    raise

