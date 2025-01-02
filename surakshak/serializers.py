from rest_framework import serializers
from .models import *


class IncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Incident
        fields = [
            "id",
            "created_at",
            "incident_type",
            "camera",
            "resolved",
            "resolver",
        ]


class RespondentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Respondent
        fields = [
            "id",
            "incident_type",
            "name",
            "phone",
            "email",
            "is_active",
        ]

class IncidentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentType
        fields = [
            "incident_code",
            "incident_name",
        ]

class CameraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Camera
        fields = [
            "id",
            "name",
            "location",
            "rtsp_url",
        ]
