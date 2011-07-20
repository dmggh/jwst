from django.conf.urls.defaults import *
from jsonrpc import jsonrpc_site

import crds.server.jsonapi.views
import crds.server.interactive.views

import crds.server.settings as settings

urlpatterns = patterns('',
  url(r'^json/browse/', 'jsonrpc.views.browse', name="jsonrpc_browser"), # for the graphical browser/web console only, omissible
  url(r'^json/', jsonrpc_site.dispatch, name="jsonrpc_mountpoint"),
  url(r'^json/(?P<method>[a-zA-Z0-9.]+)$', jsonrpc_site.dispatch), # for HTTP GET only, also omissible
  
  url(r'^bestrefs/$', 'interactive.views.bestrefs_index'),          
  url(r'^bestrefs/input/$', 'interactive.views.bestrefs_input'),          
  url(r'^bestrefs/compute/$', 'interactive.views.bestrefs_compute'),
          
#        (r'site_media/(?P<path>.*)$', 'django.views.static.serve',
#         {'document_root': settings.MEDIA_ROOT }),
#        
#        (r'site_media/(?P<path>.*/.*/.*)$', 'django.views.static.serve',
#         {'document_root': settings.MEDIA_ROOT }),

)

