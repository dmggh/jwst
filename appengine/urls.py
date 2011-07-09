# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.conf.urls.defaults import *

from jsonrpc import jsonrpc_site

import lookup.views
import crds.server.interactive.views

import crds.server.settings as settings

urlpatterns = patterns('',
    # Example:
    # (r'^foo/', include('foo.urls')),

    # Uncomment this for admin:
#     (r'^admin/', include('django.contrib.admin.urls')),

  url(r'^json/browse/', 'jsonrpc.views.browse', name="jsonrpc_browser"), # for the graphical browser/web console only, omissible
  url(r'^json/', jsonrpc_site.dispatch, name="jsonrpc_mountpoint"),
  url(r'^json/(?P<method>[a-zA-Z0-9.]+)$', jsonrpc_site.dispatch), # for HTTP GET only, also omissible
  
  url(r'^ui/bestrefs/(?P<imap>[A-Za-z0-9._]+)$', 'interactive.views.bestrefs_input'),          
  url(r'^ui/bestrefs/compute/$', 'interactive.views.bestrefs_compute'),
          
        (r'site_media/(?P<path>.*)$', 'django.views.static.serve',
         {'document_root': settings.MEDIA_ROOT }),
        
        (r'site_media/(?P<path>.*/.*/.*)$', 'django.views.static.serve',
         {'document_root': settings.MEDIA_ROOT }),


)
