"""This module supports the Django /admin/ site for CRDS."""

from django.contrib import admin
from crds.server.interactive.models import (ContextModel, ContextHistoryModel, CounterModel,
                                            FileBlob, AuditBlob, RepeatableResultBlob)
from crds.server import config
from crds.server.interactive import models

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
    
    actions = ["destroy_file"]

    if config.server_usecase in ["dev", "test"]:
        destroyable_states = models.FILE_STATES  # anything
    else:
        destroyable_states = ["uploaded"]
    
    def destroy_file(self, request, queryset):
        """Support cleaning up error conditions from failed file submissions;  
        It will destroy both the database record and server cache copy of a file.
        """
        for fileblob in queryset:
            fileblob.thaw()
            if fileblob.state in self.destroyable_states:
                fileblob.destroy()
                self.message_user(request, "DESTROYED %s with state '%s'." % (fileblob.moniker, fileblob.state))
            else:
                self.message_user(request, "SKIPPED %s non-destroyable file with state '%s' not one of '%s'." % 
                                  (fileblob.moniker, fileblob.state, self.destroyable_states))
    destroy_file.short_description = "DESTROY FILE:  permanently eliminate database and cache copy (DANGER! no confirmation)"

admin.site.register(FileBlob, FileBlobAdmin)

class AuditBlobAdmin(admin.ModelAdmin):
    search_fields = ["name"]
admin.site.register(AuditBlob, AuditBlobAdmin)

class RepeatableResultBlobAdmin(admin.ModelAdmin):
    search_fields = ["id"]
admin.site.register(RepeatableResultBlob, RepeatableResultBlobAdmin)

