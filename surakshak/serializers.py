from rest_framework import serializers
from .models import Incident, Respondent


class IncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Incident
        fields = [
            "incident_id",
            "created_at",
            "type",
            "camera_id",
            "resolved",
            "resolver",
        ]


class RespondentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Respondent
        fields = [
            "id",
            "group",
            "name",
            "phone",
            "email",
            "is_active",
        ]
