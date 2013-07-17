"""This module supports the Django /admin/ site for CRDS."""

from django.contrib import admin
from crds.server.interactive.models import (ContextModel, ContextHistoryModel, CounterModel,
                                            FileBlob, AuditBlob, RepeatableResultBlob)

class ContextModelAdmin(admin.ModelAdmin):
    search_fields = ["name"]
admin.site.register(ContextModel, ContextModelAdmin)

class ContextHistoryModelAdmin(admin.ModelAdmin):
    search_fields = ["start_date","context"]
admin.site.register(ContextHistoryModel, ContextModelAdmin)

class CounterModelAdmin(admin.ModelAdmin):
    search_fields = ["name"]
admin.site.register(CounterModel, CounterModelAdmin)

class FileBlobAdmin(admin.ModelAdmin):
    search_fields = ["name", "state"]
    
    actions = ["destroy_uploaded_file"]

    def destroy_uploaded_file(self, request, queryset):
        """Support cleaning up error conditions from failed file submissions;  
        It will destroy both the database record and server cache copy of a file.
        """
        for fileblob in queryset:
            fileblob.thaw()
            if fileblob.state == "uploaded":
                fileblob.destroy()
                self.message_user(request, "Destroyed %s." % fileblob.moniker)
            else:
                self.message_user(request, "Skipped %s non-upload state file with state '%s'." % 
                                  (fileblob.moniker, fileblob.state))
            
    destroy_uploaded_file.short_description = "Destroy uploaded file:  cleanup database and cache copy (DANGER! no confirmation)"

admin.site.register(FileBlob, FileBlobAdmin)

class AuditBlobAdmin(admin.ModelAdmin):
    search_fields = ["name"]
admin.site.register(AuditBlob, AuditBlobAdmin)

class RepeatableResultBlobAdmin(admin.ModelAdmin):
    search_fields = ["id"]
admin.site.register(RepeatableResultBlob, RepeatableResultBlobAdmin)

