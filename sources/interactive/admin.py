"""This module supports the Django /admin/ site for CRDS."""
# from builtins import str

from django.contrib import admin
from crds_server.interactive.models import (ContextModel, ContextHistoryModel, RemoteContextModel,
                                            CounterModel, FileBlob, AuditBlob, RepeatableResultBlob)
from crds_server import config
from crds_server.interactive import models, views
from crds import log

class RemoteContextModelAdmin(admin.ModelAdmin):
    search_fields = ["name"]
admin.site.register(RemoteContextModel, RemoteContextModelAdmin)

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
    
    actions = ["destroy_file", "repair_catalog"]

    if config.server_usecase in ["django", "dev"]:
        destroyable_states = models.FILE_STATES  # anything
    else:
        destroyable_states = ["uploaded"]
    
    def destroy_file(self, request, queryset):
        "DESTROY FILE:  permanently eliminate database and cache copy (DANGER! no confirmation)"
        for fileblob in queryset:
            fileblob.thaw()
            if fileblob.state in self.destroyable_states:
                fileblob.destroy()
                self.announce(request, "DESTROYED %s with state '%s'." % (fileblob.moniker, fileblob.state))
            else:
                self.announce(request, "SKIPPED %s non-destroyable file with state '%s' not one of '%s'." % 
                                  (fileblob.moniker, fileblob.state, self.destroyable_states))

    destroy_file.short_description = destroy_file.__doc__
    
    def repair_catalog(self, request, queryset):
        """Repair catalog entries by restoring information from cached references. """
        for fileblob in queryset:
            repairs, failed = fileblob.repair_defects()
            for msg in list(repairs.values()) + list(failed.values()):
                self.announce(request, "File '{}' ".format(fileblob.name) + " " + msg)
    repair_catalog.short_description = repair_catalog.__doc__
        
    def announce(self, request, message):
        self.message_user(request, message)
        log.info("User", repr(str(request.user)), message)

admin.site.register(FileBlob, FileBlobAdmin)

class AuditBlobAdmin(admin.ModelAdmin):
    search_fields = ["name"]
admin.site.register(AuditBlob, AuditBlobAdmin)

class RepeatableResultBlobAdmin(admin.ModelAdmin):

    search_fields = ["id", "name"]
    
    actions = ["display_result"]

    def display_result(self, request, queryset):
        "Display the result encoded in this results blob."
        displayed = queryset[0]
        displayed.thaw()
        return views.display_result(request, displayed.uuid)

    def announce(self, request, message):
        self.message_user(request, message)
        log.info("User", repr(str(request.user)), message)

admin.site.register(RepeatableResultBlob, RepeatableResultBlobAdmin)

