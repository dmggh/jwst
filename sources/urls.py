from django.conf.urls import *
from jsonrpc import jsonrpc_site

import crds.server.jsonapi.views
import crds.server.interactive.views

from crds.server import settings, config

urlpatterns = patterns('',
  url(r'^json/browse/', 'jsonrpc.views.browse', name="jsonrpc_browser"), # for the graphical browser/web console only, omissible
  url(r'^json/', jsonrpc_site.dispatch, name="jsonrpc_mountpoint"),
  url(r'^json/(?P<method>[a-zA-Z0-9_.]+)$', jsonrpc_site.dispatch), # for HTTP GET only, also omissible
  
  url(r'^$', 'crds.server.interactive.views.index'),          

  url(r'^login/$', 'crds.server.interactive.views.login'),          
  url(r'^logout/$', 'crds.server.interactive.views.logout'),          

  url(r'^bestrefs/$', 'crds.server.interactive.views.bestrefs'),          
  url(r'^bestrefs_explore/$', 'crds.server.interactive.views.bestrefs_explore'),          
  url(r'^bestrefs_explore_compute/$', 'crds.server.interactive.views.bestrefs_explore_compute'), 

  url(r'^set_file_enable/$',    'crds.server.interactive.views.set_file_enable'),          

  url(r'^certify/$',      'crds.server.interactive.views.certify_file'),          
  url(r'^difference/$',   'crds.server.interactive.views.difference_files'),
  url(r'^difference/(\w+)/(\w+)/$', 'crds.server.interactive.views.difference_files'),
  url(r'^recent_activity/$', 'crds.server.interactive.views.recent_activity'),        

  url(r'^create_contexts/$', 'crds.server.interactive.views.create_contexts'),        

  url(r'^submit/(?P<crds_filetype>reference|mapping)/$', 'crds.server.interactive.views.submit_files'),
  
  (r'^upload/list/$', 'crds.server.interactive.views.upload_list', {}, 'upload-list'),
  (r'^upload/new/$', 'crds.server.interactive.views.upload_new', {}, 'upload-new'),
  (r'^upload/delete/(?P<filename>[A-Za-z0-9_.]+)$', 'crds.server.interactive.views.upload_delete', {}, 'upload-delete'),
            
  url(r'^batch_submit_references/$', 'crds.server.interactive.views.batch_submit_references'),
  url(r'^submit_confirm/$', 'crds.server.interactive.views.submit_confirm'),
          
  url(r'^browse/(?P<filename>[A-Za-z0-9_.]+(fits|imap|rmap|pmap|r\dh))$', 
      'crds.server.interactive.views.browse_known_file'),
  url(r'^browse_db/$', 'crds.server.interactive.views.browse_db'),        

  # Simple get is screed against the database and redirected
  url(r'^get/(?P<filename>[A-Za-z0-9_.]+(fits|imap|rmap|pmap|r\dh))$', 
      'crds.server.interactive.views.brokered_get'),
  # Here Django serves the file,  unchecked,  simple but not recommended.
  # Ultimately this will be replaced by a better static server,  maybe the archive.
  # At that point the whole URL will change but not the semantics.
  url(r'^unchecked_get/(?P<filename>[A-Za-z0-9_.]+(fits|imap|rmap|pmap|r\dh))$', 
      'crds.server.interactive.views.get_file_data'),
  url(r'^get_archive/(?P<filename>[A-Za-z0-9_.]+(tar\.gz|tar\.bz2|tar))$', 
      'crds.server.interactive.views.get_archive'),

  url(r'^version_info/$', 
      'crds.server.interactive.views.version_info'),

  url(r'^set_default_context/$', 
      'crds.server.interactive.views.set_default_context'),
  url(r'^display_context_history/$', 
      'crds.server.interactive.views.display_context_history'),
                       

  url(r'^display_result/(?P<results_id>\d+)$', 
      'crds.server.interactive.views.display_result'),

#        (r'site_media/(?P<path>.*)$', 'django.views.static.serve',
#         {'document_root': settings.MEDIA_ROOT }),
#        
#        (r'site_media/(?P<path>.*/.*/.*)$', 'django.views.static.serve',
#         {'document_root': settings.MEDIA_ROOT }),

)

from django.contrib.staticfiles.urls import staticfiles_urlpatterns
if config.servertype == "django":
    urlpatterns += staticfiles_urlpatterns()

# urls.py
from django.conf.urls import patterns, url, include
from django.contrib import admin

admin.autodiscover()

urlpatterns += patterns('',
    (r'^admin/', include(admin.site.urls)),
)


urlpatterns += patterns('',
    # url(r'^upload/', include('fileupload.urls')),
)
