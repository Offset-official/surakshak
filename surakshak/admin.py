from django.contrib import admin
from .models import *

## Customizing the admin interface

class RespondentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'phone', 'email', 'is_active', 'incident_types_display')  # Custom display for incident types

    def incident_types_display(self, obj):
        # Access incident types through the reverse relationship
        return ", ".join([incident.type_name for incident in obj.incident_types.all()])

    incident_types_display.short_description = "Incident Types"

    def save_model(self, request, obj, form, change):
        incident_types = form.cleaned_data['incident_types']
        obj.incident_types.set(incident_types.distinct())  # 'distinct' ensures unique items

        super().save_model(request, obj, form, change)

class IncidentAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'incident_type', 'camera', 'resolved', 'resolver')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "incident_type":
            # Retrieve all IncidentType objects
            all_incident_types = IncidentType.objects.all()
            
            # Manually filter duplicates based on 'type_name'
            seen = set()
            unique_incident_types = []
            for incident_type in all_incident_types:
                if incident_type.type_name not in seen:
                    unique_incident_types.append(incident_type)
                    seen.add(incident_type.type_name)

            # Return a queryset with unique incident types
            kwargs["queryset"] = IncidentType.objects.filter(id__in=[incident.id for incident in unique_incident_types])
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class CameraAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'location', 'rtsp_url')
    # disable url checks

class IncidentTypeAdmin(admin.ModelAdmin):
    list_display = ('type_name', 'respondents_display')  # Custom display for respondents
    list_filter = ('type_name',)

    def respondents_display(self, obj):
        # Access respondents through the reverse relationship
        return ", ".join([respondent.name for respondent in obj.respondents.all()])

    respondents_display.short_description = "Respondents"

class InferenceScheduleAdmin(admin.ModelAdmin):
    list_display = ('id', 'start_time', 'end_time', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')

    

## Registering models with the admin site
admin.site.register(Respondent, RespondentAdmin)
admin.site.register(Camera, CameraAdmin)
admin.site.register(Incident, IncidentAdmin)
admin.site.register(IncidentType, IncidentTypeAdmin)
admin.site.register(InferenceSchedule)
admin.site.register(Log)