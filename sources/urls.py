from django.conf.urls import *

from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView

from jsonrpc import jsonrpc_site

import crds.server.jsonapi.views
import crds.server.interactive.views
from crds.server.jpoll.views import JPOLL_KEY_RE_STR

from crds.server import settings, config
from crds.server.interactive.common import UUID_RE_STR
from crds.config import FILE_RE_STR

# XXX Cached views must be completely defined by the URL
# XXX GET/POST parameters and cookies don't count to differentiate pages.
# XXX Don't cache authenticated pages (@login_required).
MAX_AGE = None  # seconds,  or forever for None
crds_cacher = cache_page(MAX_AGE, cache='crds_cache')

urlpatterns = patterns('',

    (r'^robots\.txt$', TemplateView.as_view(template_name="robots.txt", content_type='text/plain')),
 
    # url(r'^json/browse/', 'jsonrpc.views.browse', name="jsonrpc_browser"), # for the graphical browser/web console only, omissible

    # Original json rpc POST URL format:   /json/
    # Enhanced json rpc POST URL format for logging:   /json/<ignored_method_name>/<ignored_rpc_uuid>/
    # The enhanced URL contains additional information for "friendly" logging only;  it is redundant and ignored.
    # Technically,  it's possible for the URL to lie about the contents of the JSON RPC POST parameters,  
    #     i.e. really a different method or id.
    # NOTE: old-style uninformative /json/ URLs are still accepted to support older clients
    url(r'^json/', jsonrpc_site.dispatch, name="jsonrpc_mountpoint"),  # this URL currently supports ALL /json/ formats
    
    # url(r'^json/(?P<method>[a-zA-Z0-9_.]+)$', jsonrpc_site.dispatch), # for HTTP GET only, also omissible,  XSS safe??
    
    url(r'^$', 'crds.server.interactive.views.index'),          
    
    url(r'^login/$', 'crds.server.interactive.views.login'),          
    url(r'^logout/$', 'crds.server.interactive.views.logout'),
    url(r'^set_password/$', 'crds.server.interactive.views.set_password'),          
    url(r'^lock_status/$', 'crds.server.interactive.views.lock_status'),         
    
    url(r'^monitor/(?P<process_key>{0})/$'.format(JPOLL_KEY_RE_STR), 'crds.server.interactive.views.monitor_process'),

    url(r'^bestrefs/$', 'crds.server.interactive.views.bestrefs'),          
    url(r'^bestrefs_explore/$', 'crds.server.interactive.views.bestrefs_explore'),          
    url(r'^bestrefs_explore_compute/$', 'crds.server.interactive.views.bestrefs_explore_compute'), 
    url(r'^docs/(?P<page>[A-Za-z0-9_.]+)/$', 'crds.server.interactive.views.docs'),
    
    url(r'^mark_bad/$',    'crds.server.interactive.views.mark_bad'),          
    
    url(r'^certify/$',      'crds.server.interactive.views.certify_file'),          
    url(r'^difference/$',   'crds.server.interactive.views.difference_files'),
    url(r'^difference/{0}/{1}/$'.format(FILE_RE_STR, FILE_RE_STR), 
        crds_cacher(crds.server.interactive.views.difference_files)),
    url(r'^recent_activity/$', 'crds.server.interactive.views.recent_activity'),        
    url(r'^delivery_status/$', 'crds.server.interactive.views.delivery_status'),        
    url(r'^old_results/$', 'crds.server.interactive.views.old_results'),        
    
    url(r'^create_contexts/$', 'crds.server.interactive.views.create_contexts'),        
    
    url(r'^submit/(?P<crds_filetype>reference|mapping)/$', 'crds.server.interactive.views.submit_files'),
    
    (r'^upload/list/$', 'crds.server.interactive.views.upload_list', {}, 'upload-list'),
    (r'^upload/new/$', 'crds.server.interactive.views.upload_new', {}, 'upload-new'),
    (r'^upload/delete/(?P<filename>{0})$'.format(FILE_RE_STR),
     'crds.server.interactive.views.upload_delete', {}, 'upload-delete'),
              
    # (r'^upload/alt_new/$', 'crds.server.interactive.views.upload_alt_new', {}, 'upload-alt-new'),

    url(r'^batch_submit_references/$', 'crds.server.interactive.views.batch_submit_references'),
    url(r'^submit_confirm/$', 'crds.server.interactive.views.submit_confirm'),

    url(r'^delete/reference/$', 'crds.server.interactive.views.delete_references'),
    url(r'^add_existing/reference/$', 'crds.server.interactive.views.add_existing_references'),
            
    url(r'^browse/(?P<filename>{0})$'.format(FILE_RE_STR), 
        crds_cacher(crds.server.interactive.views.browse_known_file)),
    url(r'^browse_db/$', 'crds.server.interactive.views.browse_db'),

    url(r'^uses/(?P<filename>{0})$'.format(FILE_RE_STR),
        crds.server.interactive.views.uses_view),

    url(r'^context_table/(?P<mapping>{0})/?$'.format(FILE_RE_STR, FILE_RE_STR),
        'crds.server.interactive.views.context_table'),
    url(r'^context_table/(?P<mapping>{0})/(?P<recursive>\d+)$'.format(FILE_RE_STR), 
        'crds.server.interactive.views.context_table'),
    
    # Simple get is screened against the database and redirected
    url(r'^get/(?P<filename>{0})/?$'.format(FILE_RE_STR), 
        'crds.server.interactive.views.brokered_get'),

    #     url(r'^get_archive/(?P<filename>{0})$'.format(FILE_RE_STR), 
    #         'crds.server.interactive.views.get_archive'),

    url(r'^version_info/$', 
        'crds.server.interactive.views.version_info'),
    
    url(r'^set_default_context/$', 
        'crds.server.interactive.views.set_default_context'),
    url(r'^display_context_history/$', 
        crds.server.interactive.views.display_context_history),
    url(r'^display_all_contexts/$', 
        crds.server.interactive.views.display_all_contexts),
                         
    url(r'^display_result/(?P<results_id>{0})$'.format(UUID_RE_STR), 
        'crds.server.interactive.views.display_result'),
                       
    url(r'^edit_context_history/(?P<history_id>\d+)/{0}/$'.format(FILE_RE_STR), 
        'crds.server.interactive.views.edit_context_history'),                    
                         
    url(r'^jpoll/open_channel/$', 'crds.server.jpoll.views.open_channel'),
    url(r'^jpoll/pull_messages/(?P<channel_id>{})/(?P<since_id>\-?\d+)/$'.format(UUID_RE_STR), 
        'crds.server.jpoll.views.pull_messages'),
    
#     url(r'^jpoll/test_page/$', 'crds.server.jpoll.views.test_page'),
#     url(r'^jpoll/test_worker/$', 'crds.server.jpoll.views.test_worker'),
#     url(r'^jpoll/test_response/$', 'crds.server.jpoll.views.test_response'),

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

    # ...  django-smuggler ....
    (r'^admin/', include('smuggler.urls')),  # before admin url patterns!
    (r'^admin/', include(admin.site.urls)),
    # ...  django-smuggler ....
    
    (r'^admin/', include(admin.site.urls)),
)


urlpatterns += patterns('',
    # url(r'^upload/', include('fileupload.urls')),
)

if config.DEBUG:
    urlpatterns += patterns('', 
        (r'^/debug_command/$', crds.server.interactive.views.debug_command),
        #         (r'^get_archive/(?P<filename>{0})$'.format(FILE_RE_STR),
        #             'crds.server.interactive.views.get_archive'),
        
        # Here Django serves the file,  unchecked,  simple but not recommended.
        # Ultimately this will be replaced by a better static server,  maybe the archive.
        # At that point the whole URL will change but not the semantics.
        (r'^unchecked_get/(references|mappings)/(hst|jwst)/(?P<filename>{0})$'.format(FILE_RE_STR),
         crds.server.interactive.views.unchecked_get),
    )
