from django.contrib import admin
from .models import *

## Customizing the admin interface

class RespondentAdmin(admin.ModelAdmin):
    list_display = ('id','name', 'phone', 'email', 'is_active', 'incident_types_display')
    filter_horizontal = ('incident_type',)

    def incident_types_display(self, obj):
        return ", ".join([incident.type_name for incident in obj.incident_type.all()])

    # Overriding default save method to save many-to-many field
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.incident_type.set(form.cleaned_data['incident_type'])

    incident_types_display.short_description = "Incident Types"

class IncidentAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'incident_type', 'camera', 'resolved', 'resolver')

class CameraAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'location', 'rtsp_url')



## Registering models with the admin site
admin.site.register(Respondent, RespondentAdmin)
admin.site.register(Camera, CameraAdmin)
admin.site.register(Incident, IncidentAdmin)
admin.site.register(IncidentType)
