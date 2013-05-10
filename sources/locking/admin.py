from django.contrib import admin

from .models import Lock


class LockAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_on'
    list_display = ('locked_object', 'created_on', 'max_age', 'expires_on', 'is_expired')
admin.site.register(Lock, LockAdmin)
