"""This module supports the Django /admin/ site for CRDS."""

from django.contrib import admin
from crds.server.interactive.models import (ContextModel, CounterModel,
                                            FileBlob, AuditBlob, RepeatableResultBlob)

class ContextModelAdmin(admin.ModelAdmin):
    search_fields = ["name"]
admin.site.register(ContextModel, ContextModelAdmin)

class CounterModelAdmin(admin.ModelAdmin):
    search_fields = ["name"]
admin.site.register(CounterModel, CounterModelAdmin)

class FileBlobAdmin(admin.ModelAdmin):
    search_fields = ["name"]
admin.site.register(FileBlob, FileBlobAdmin)

class AuditBlobAdmin(admin.ModelAdmin):
    search_fields = ["name"]
admin.site.register(AuditBlob, AuditBlobAdmin)

class RepeatableResultBlobAdmin(admin.ModelAdmin):
    search_fields = ["id"]
admin.site.register(RepeatableResultBlob, RepeatableResultBlobAdmin)