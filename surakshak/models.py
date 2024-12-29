from datetime import datetime
from django.db import models
from django.utils import timezone

class Incident(models.Model):
   
    INCIDENT_TYPES = {
        "T" : "Tresspassing",
        "F" : "Fire",
        "S" : "Suspicious",
    }

    incident_id = models.AutoField(primary_key = True)
    created_at = models.DateTimeField(timezone.now)
    type = models.CharField(max_length = 1, choices = INCIDENT_TYPES.items())
    severity = models.IntegerField()
    camera_id = models.IntegerField()
    resolved = models.BooleanField(default = False)
    resolver = models.ForeignKey('Respondent', on_delete = models.CASCADE, null = True)


class Respondent(models.Model):

    id = models.AutoField(primary_key = True)
    group = models.CharField(max_length = 5)    #define groups later
    name = models.CharField(max_length = 100)
    phone = models.CharField(max_length = 10)
    email = models.EmailField()
    is_active = models.BooleanField(default = True)
    is_admin = models.BooleanField(default = False)


class Incident_to_Respondent(models.Model):
    
    INCIDENT_TYPES = {
        "T" : "Tresspassing",
        "F" : "Fire",
        "S" : "Suspicious",
    }

    incident_id = models.AutoField(primary_key = True)
    respondent_id = models.ForeignKey('Respondent', on_delete = models.CASCADE)

class Camera(models.Model):

    # id should be auto increment
    name = models.CharField(max_length = 100)
    id = models.AutoField(primary_key = True)
    location = models.CharField(max_length = 100)
    rtsp_url = models.CharField(max_length = 100)
