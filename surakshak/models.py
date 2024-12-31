from django.db import models
from django.utils import timezone


class Incidents_types(models.Model):

    INCIDENT_TYPES = [
        ("T", "Tresspassing"),
        ("F", "Fire"),
        ("S", "Suspicious"),
    ]

    id = models.AutoField(primary_key=True)
    incident_type = models.CharField(max_length=1, choices=INCIDENT_TYPES)

    # To display the incident type instead of object representation
    def __str__(self):
        return self.incident_type

class Incident(models.Model):

    incident_id = models.AutoField(primary_key = True)
    created_at = models.DateTimeField(timezone.now)
    type = models.ForeignKey('Incidents_types', on_delete = models.CASCADE)
    camera_id = models.ForeignKey('Cameras', on_delete = models.CASCADE)
    resolved = models.BooleanField(default = False)
    resolver = models.ForeignKey('Respondents', on_delete = models.CASCADE, null = True)


class Respondents(models.Model):

    id = models.AutoField(primary_key = True)
    group = models.ForeignKey('Incidents_types', on_delete = models.CASCADE)
    name = models.CharField(max_length = 100)
    phone = models.CharField(max_length = 10)
    email = models.EmailField(max_length = 100)
    is_active = models.BooleanField(default = True)

    def __str__(self):
        return f"{self.name}, {self.phone}, {self.email}, {self.is_active}"


class Cameras(models.Model):

    id = models.AutoField(primary_key = True)
    name = models.CharField(max_length = 100, unique=True)
    location = models.CharField(max_length = 100)
    rtsp_url = models.CharField(max_length = 100)