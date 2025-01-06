from django.db import models
from django.utils.timezone import now


class IncidentType(models.Model):
    type_name = models.CharField(max_length=50, null=True)  # e.g., "Trespassing", "Fire"
    respondents = models.ManyToManyField("Respondent", related_name="incident_types", null=True)  # Respondents for this type

    def __str__(self):
        return f"{self.type_name}"


class Camera(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=100, null=True)
    rtsp_url = models.CharField(max_length=200)  # Updated to URLField for clarity

    def __str__(self):
        return self.name


class Respondent(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=10)
    email = models.EmailField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Incident(models.Model):
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(default=now)  
    incident_type = models.CharField(max_length=200)
    # incident_type = models.ForeignKey("IncidentType", on_delete=models.CASCADE, null=True)  
    # camera = models.ForeignKey("Camera", on_delete=models.CASCADE, related_name="name") 
    camera = models.CharField(max_length=200)
    resolved = models.BooleanField(default=False)
    image = models.ImageField(null=True)
    resolver = models.ForeignKey("Respondent", on_delete=models.CASCADE, null=True, blank=True)  
    
    def __str__(self):
        return f"Incident {self.id} - {self.incident_type}"

class InferenceSchedule(models.Model):
    id = models.AutoField(primary_key=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    # checkboxes for days
    monday = models.BooleanField(default=True)
    tuesday = models.BooleanField(default=True)
    wednesday = models.BooleanField(default=True)
    thursday = models.BooleanField(default=True)
    friday = models.BooleanField(default=True)
    saturday = models.BooleanField(default=True)
    sunday = models.BooleanField(default=True)

    # add constrint that only 1 item can be in the model
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(id=1), name="single_inference_schedule"
            )
        ]
    
class Log(models.Model):
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(default=now)
    log = models.TextField()

    def __str__(self):
        return f"Log {self.id}"