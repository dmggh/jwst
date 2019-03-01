from django.conf.urls import *

from django.views.decorators.cache import cache_page

from jsonrpc import jsonrpc_site

import crds_server.jsonapi.views
import crds_server.interactive.views
import crds_server.jpoll.views
import crds_server.submission_form.views

from crds_server.jpoll.views import JPOLL_KEY_RE_STR
from crds_server import settings, config
from crds_server.interactive.common import UUID_RE_STR

from crds.core.config import FILE_RE_STR, USER_NAME_RE_STR

# XXX Cached views must be completely defined by the URL
# XXX GET/POST parameters and cookies don't count to differentiate pages.
# XXX Don't cache authenticated pages (@login_required).
MAX_AGE = None  # seconds,  or forever for None
crds_cacher = cache_page(MAX_AGE, cache='crds_cache')

urlpatterns = [

    # url(r'^json/browse/', jsonrpc.views.browse, name="jsonrpc_browser"), # for the graphical browser/web console only, omissible

    # Original json rpc POST URL format:   /json/
    # Enhanced json rpc POST URL format for logging:   /json/<ignored_method_name>/<ignored_rpc_uuid>/
    # The enhanced URL contains additional information for "friendly" logging only;  it is redundant and ignored.
    # Technically,  it's possible for the URL to lie about the contents of the JSON RPC POST parameters,  
    #     i.e. really a different method or id.
    # NOTE: old-style uninformative /json/ URLs are still accepted to support older clients
    url(r'^json/', jsonrpc_site.dispatch, name="jsonrpc_mountpoint"),  # this URL currently supports ALL /json/ formats
    
    # url(r'^json/(?P<method>[a-zA-Z0-9_.]+)$', jsonrpc_site.dispatch), # for HTTP GET only, also omissible,  XSS safe??
    
    url(r'^$', crds_server.interactive.views.index),          
    
    url(r'^login/$', crds_server.interactive.views.login),          
    url(r'^logout/$', crds_server.interactive.views.logout),
    url(r'^set_password/$', crds_server.interactive.views.set_password),          
    url(r'^lock_status/((?P<user>{0})/)?$'.format(USER_NAME_RE_STR), crds_server.interactive.views.lock_status),         
    
    url(r'^monitor/(?P<process_key>{0})/$'.format(JPOLL_KEY_RE_STR), crds_server.interactive.views.monitor_process),

    url(r'^bestrefs/$', crds_server.interactive.views.bestrefs),          
    url(r'^bestrefs_explore/$', crds_server.interactive.views.bestrefs_explore),          
    url(r'^bestrefs_explore_compute/$', crds_server.interactive.views.bestrefs_explore_compute), 
    url(r'^docs/(?P<page>[A-Za-z0-9_.]+)/$', crds_server.interactive.views.docs),
    
    url(r'^mark_bad/$',    crds_server.interactive.views.mark_bad),          
    
    url(r'^certify/$',      crds_server.interactive.views.certify_file),          
    url(r'^difference/$',   crds_server.interactive.views.difference_files),
    url(r'^difference/{0}/{1}/$'.format(FILE_RE_STR, FILE_RE_STR), 
        crds_cacher(crds_server.interactive.views.difference_files)),
    url(r'^recent_activity_input/$', crds_server.interactive.views.recent_activity_input),              # form
    url(r'^recent_activity_query/$', crds_server.interactive.views.recent_activity_query),  # GET or POST query
    url(r'^delivery_status/$', crds_server.interactive.views.delivery_status),        
    url(r'^old_results/$', crds_server.interactive.views.old_results),        
    
    url(r'^create_contexts/$', crds_server.interactive.views.create_contexts),        
    
    url(r'^submit/(?P<crds_filetype>reference|mapping)/$', crds_server.interactive.views.submit_files),
    
    url(r'^upload/list/$', crds_server.interactive.views.upload_list, name="upload-list"), #, {}, 'upload-list'),
    url(r'^upload/new/$', crds_server.interactive.views.upload_new, name="upload-new"), #, {}, 'upload-new'),
    url(r'^upload/delete/(?P<filename>{0})$'.format(FILE_RE_STR),
        crds_server.interactive.views.upload_delete, name="upload-delete"), #, {}, 'upload-delete'),
              
    # url(r'^upload/alt_new/$', 'crds_server.interactive.views.upload_alt_new'), # {}, 'upload-alt-new'),

    url(r'^batch_submit_references/$', crds_server.interactive.views.batch_submit_references),
    url(r'^submit_confirm/$', crds_server.interactive.views.submit_confirm),

    url(r'^delete/reference/$', crds_server.interactive.views.delete_references),
    url(r'^add_existing/reference/$', crds_server.interactive.views.add_existing_references),
            
    url(r'^browse/(?P<filename>{0})$'.format(FILE_RE_STR), 
        crds_cacher(crds_server.interactive.views.browse_known_file)),
    url(r'^browse_db/$', crds_server.interactive.views.browse_db),

    url(r'^uses/(?P<filename>{0})$'.format(FILE_RE_STR),
        crds_server.interactive.views.uses_view),

    url(r'^context_table/(?P<mapping>{0})/?$'.format(FILE_RE_STR, FILE_RE_STR),
        crds_server.interactive.views.context_table),
    url(r'^context_table/(?P<mapping>{0})/(?P<recursive>\d+)$'.format(FILE_RE_STR), 
        crds_server.interactive.views.context_table),
    
    # Simple get is screened against the database and redirected
    url(r'^get/(?P<filename>{0})/?$'.format(FILE_RE_STR), 
        crds_server.interactive.views.brokered_get),

    #     url(r'^get_archive/(?P<filename>{0})$'.format(FILE_RE_STR), 
    #         'crds_server.interactive.views.get_archive'),

    url(r'^version_info/$', 
        crds_server.interactive.views.version_info),
    
    url(r'^set_default_context/$', 
        crds_server.interactive.views.set_default_context),
    url(r'^display_context_history/$', 
        crds_server.interactive.views.display_context_history),
    url(r'^display_all_contexts/$', 
        crds_server.interactive.views.display_all_contexts),
                         
    url(r'^display_result/(?P<results_id>{0})$'.format(UUID_RE_STR), 
        crds_server.interactive.views.display_result),
                       
    url(r'^authenticated_result/(?P<results_id>{0})$'.format(UUID_RE_STR), 
        crds_server.interactive.views.authenticated_result),
                       
    url(r'^edit_context_history/(?P<history_id>\d+)/{0}/$'.format(FILE_RE_STR), 
        crds_server.interactive.views.edit_context_history),                    
                         
    url(r'^jpoll/open_channel/$', crds_server.jpoll.views.open_channel),
    url(r'^jpoll/pull_messages/(?P<channel_id>{})/(?P<since_id>\-?\d+)/$'.format(UUID_RE_STR), 
        crds_server.jpoll.views.pull_messages),
    
    url(r'^submission_form/redcat_submit/$', crds_server.submission_form.views.redcat_submit),
    url(r'^submission_form/(?P<id>[0-9]+)/$', crds_server.submission_form.views.redcat_id_detail, name='redcat_id_detail'),

    url(r'^submission_form/redcat_list/$', crds_server.submission_form.views.redcat_list),

#     url(r'^jpoll/test_page/$', 'crds_server.jpoll.views.test_page'),
#     url(r'^jpoll/test_worker/$', 'crds_server.jpoll.views.test_worker'),
#     url(r'^jpoll/test_response/$', 'crds_server.jpoll.views.test_response'),

]

from django.contrib.staticfiles.urls import staticfiles_urlpatterns
if config.servertype == "django":
    urlpatterns += staticfiles_urlpatterns()

# urls.py
from django.conf.urls import url, include
from django.contrib import admin

import smuggler.urls

admin.autodiscover()

urlpatterns += [

    # ...  django-smuggler ....
    url(r'^admin/', include(smuggler.urls)),  # before admin url patterns!
    # ...  django-smuggler ....
    
    url(r'^admin/', include(admin.site.urls)),   # AFTER smuggler
]


urlpatterns += [
    # url(r'^upload/', include('fileupload.urls')),
]

if config.DEBUG:
    urlpatterns += [
        url(r'^debug_command/$', crds_server.interactive.views.debug_command),
        #         (r'^get_archive/(?P<filename>{0})$'.format(FILE_RE_STR),
        #             'crds_server.interactive.views.get_archive'),
        
        # Here Django serves the file,  unchecked,  simple but not recommended.
        # Ultimately this will be replaced by a better static server,  maybe the archive.
        # At that point the whole URL will change but not the semantics.
        url(r'^unchecked_get/(references|mappings)/(hst|jwst)/(?P<filename>{0})$'.format(FILE_RE_STR),
            crds_server.interactive.views.unchecked_get),
    ]
