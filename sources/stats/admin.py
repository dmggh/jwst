"""This module supports the Django /admin/ site for CRDS."""

from django.contrib import admin
from crds.server.stats.models import (LogModel)

class LogModelAdmin(admin.ModelAdmin):
    search_fields = ["date","event"]    
admin.site.register(LogModel, LogModelAdmin)

