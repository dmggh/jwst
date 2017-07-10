"""This module supports the Django /admin/ site for CRDS."""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from django.contrib import admin
from .models import (ChannelModel, MessageModel)

class ChannelModelAdmin(admin.ModelAdmin):
    search_fields = ["last_returned", "key"]
admin.site.register(ChannelModel, ChannelModelAdmin)

class MessageModelAdmin(admin.ModelAdmin):
    search_fields = ["channel","timestamp","json"]
admin.site.register(MessageModel, MessageModelAdmin)

