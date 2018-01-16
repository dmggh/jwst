from django.contrib import admin
from django.db import models
from django import forms

# Register your models here.

from django.contrib import admin
from crds.server.forms.models import CrdsRequestModel

class CrdsRequestModelAdmin(admin.ModelAdmin):
    search_fields = ["title", "requester", "description_of_functionality", "date_needed"]
    formfield_overrides = {
        models.CharField: {'widget': forms.TextInput(attrs={'size':75})},
        models.TextField: {'widget': forms.Textarea(attrs={'rows':8, 'cols':75})},
    }

admin.site.register(CrdsRequestModel, CrdsRequestModelAdmin)

