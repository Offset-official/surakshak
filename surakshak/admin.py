from django.contrib import admin
from .models import Camera, Incident, Respondent, Incidents_types

admin.site.register(Camera)
admin.site.register(Incident)
admin.site.register(Respondent)
admin.site.register(Incidents_types)
