"""This module supports the Django /admin/ site for CRDS."""
from django.contrib import admin
from .models import (ChannelModel, MessageModel)

class ChannelModelAdmin(admin.ModelAdmin):
    search_fields = ["last_returned", "key"]
admin.site.register(ChannelModel, ChannelModelAdmin)

class MessageModelAdmin(admin.ModelAdmin):
    search_fields = ["channel","timestamp","json"]
admin.site.register(MessageModel, MessageModelAdmin)

