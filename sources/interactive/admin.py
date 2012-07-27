"""This module supports the Django /admin/ site for CRDS."""

from django.contrib import admin
from crds.server.interactive.models import (FileBlob, ContextBlob, 
                                            AuditBlob, CounterBlob)

class FileBlobAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    
admin.site.register(FileBlob, FileBlobAdmin)

class ContextBlobAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    pass
admin.site.register(ContextBlob, ContextBlobAdmin)

class AuditBlobAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    pass
admin.site.register(AuditBlob, AuditBlobAdmin)

class CounterBlobAdmin(admin.ModelAdmin):
    search_fields = ["name"]
admin.site.register(CounterBlob, CounterBlobAdmin)

