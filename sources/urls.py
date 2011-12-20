from django.conf.urls.defaults import *
from jsonrpc import jsonrpc_site

import crds.server.jsonapi.views
import crds.server.interactive.views

import crds.server.settings as settings

urlpatterns = patterns('',
  url(r'^json/browse/', 'jsonrpc.views.browse', name="jsonrpc_browser"), # for the graphical browser/web console only, omissible
  url(r'^json/', jsonrpc_site.dispatch, name="jsonrpc_mountpoint"),
  url(r'^json/(?P<method>[a-zA-Z0-9.]+)$', jsonrpc_site.dispatch), # for HTTP GET only, also omissible
  
  url(r'^$', 'crds.server.interactive.views.index'),          

  url(r'^login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}),          
  url(r'^logout/$', 'crds.server.interactive.views.logout'),          

  url(r'^bestrefs/$', 'crds.server.interactive.views.bestrefs'),          
  url(r'^bestrefs_explore/$', 'crds.server.interactive.views.bestrefs_explore'),          
  url(r'^bestrefs_explore_compute/$', 'crds.server.interactive.views.bestrefs_explore_compute'), 

  url(r'^submit/(?P<crds_filetype>reference|mapping)/$', 'crds.server.interactive.views.submit_file'),          
  url(r'^delivery_options/$', 'crds.server.interactive.views.delivery_options'),          
  url(r'^delivery_process/$',   'crds.server.interactive.views.delivery_process'),          
  url(r'^deliver_context/$', 'crds.server.interactive.views.deliver_context'),          
  url(r'^blacklist/$',    'crds.server.interactive.views.blacklist_file'),          
  url(r'^using/$',        'crds.server.interactive.views.using_file'),          
  url(r'^matches/$',        'crds.server.interactive.views.file_matches'),          
  url(r'^certify/$',      'crds.server.interactive.views.certify_file'),          
  url(r'^difference/$',   'crds.server.interactive.views.difference_files'),
  url(r'^reserve_name/$', 'crds.server.interactive.views.reserve_name'),        
  url(r'^recent_activity/$', 'crds.server.interactive.views.recent_activity'),        

  url(r'^create_contexts/$', 'crds.server.interactive.views.create_contexts'),        

  url(r'^edit_rmap_browse/$', 'crds.server.interactive.views.edit_rmap_browse'),        
  url(r'^edit_rmap/((?P<filename>[A-Za-z0-9_.]+rmap)/)?$', 'crds.server.interactive.views.edit_rmap'),        
          
  url(r'^browse/(?P<filename>[A-Za-z0-9_.]+(fits|imap|rmap|pmap|r\dh))$', 
      'crds.server.interactive.views.browse_known_file'),
  url(r'^browse_db/$', 'crds.server.interactive.views.browse_db'),        

  url(r'^get/(?P<filename>[A-Za-z0-9_.]+(fits|imap|rmap|pmap|r\dh))$', 
      'crds.server.interactive.views.get_file_data'),

#        (r'site_media/(?P<path>.*)$', 'django.views.static.serve',
#         {'document_root': settings.MEDIA_ROOT }),
#        
#        (r'site_media/(?P<path>.*/.*/.*)$', 'django.views.static.serve',
#         {'document_root': settings.MEDIA_ROOT }),

)

from django.contrib.staticfiles.urls import staticfiles_urlpatterns
urlpatterns += staticfiles_urlpatterns()



