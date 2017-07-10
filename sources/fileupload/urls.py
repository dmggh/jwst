from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from django.conf.urls import *
from fileupload.views import PictureCreateView, PictureDeleteView

urlpatterns = patterns('',
    (r'^new/$', PictureCreateView.as_view(), {}, 'upload-new'),
    (r'^delete/(?P<pk>\d+)$', PictureDeleteView.as_view(), {}, 'upload-delete'),
)

