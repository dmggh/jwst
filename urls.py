from django.conf.urls.defaults import *
from jsonrpc import jsonrpc_site

import crds.server.jsonapi.views
import crds.server.interactive.views

import crds.server.settings as settings

urlpatterns = patterns('',
  url(r'^json/browse/', 'jsonrpc.views.browse', name="jsonrpc_browser"), # for the graphical browser/web console only, omissible
  url(r'^json/', jsonrpc_site.dispatch, name="jsonrpc_mountpoint"),
  url(r'^json/(?P<method>[a-zA-Z0-9.]+)$', jsonrpc_site.dispatch), # for HTTP GET only, also omissible
  
  url(r'^$', 'interactive.views.index'),          

  url(r'^login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}),          
  url(r'^logout/$', 'interactive.views.logout'),          

  url(r'^bestrefs/$', 'interactive.views.bestrefs_index'),          
  url(r'^bestrefs/input/$', 'interactive.views.bestrefs_input'),          
  url(r'^bestrefs/compute/$', 'interactive.views.bestrefs_compute'),

  url(r'^submit/$', 'interactive.views.submit_file'),          
  url(r'^blacklist/$', 'interactive.views.blacklist_file'),          
  url(r'^using/$', 'interactive.views.using_file'),          
  url(r'^certify/$', 'interactive.views.certify_file'),          
  url(r'^difference/$', 'interactive.views.difference_files'),          
          
#        (r'site_media/(?P<path>.*)$', 'django.views.static.serve',
#         {'document_root': settings.MEDIA_ROOT }),
#        
#        (r'site_media/(?P<path>.*/.*/.*)$', 'django.views.static.serve',
#         {'document_root': settings.MEDIA_ROOT }),

)

from django.contrib.staticfiles.urls import staticfiles_urlpatterns
urlpatterns += staticfiles_urlpatterns()



