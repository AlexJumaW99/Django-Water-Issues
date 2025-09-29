from django.db import models
from django.contrib.auth.models import User
import json
from jsonfield import JSONField

class Municipality(models.Model):
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=50)  # city, town, rm
    population_2021 = models.IntegerField(default=0)
    geometry = JSONField()  # Store GeoJSON geometry
    properties = JSONField(default=dict)  # Additional properties

    def __str__(self):
        return f"{self.status.title()} of {self.name}"

class Park(models.Model):
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=100, blank=True)
    management = models.CharField(max_length=100, blank=True)
    owner = models.CharField(max_length=100, blank=True)
    park_class = models.CharField(max_length=100, blank=True)
    url = models.URLField(blank=True)
    geometry = JSONField()
    properties = JSONField(default=dict)

    def __str__(self):
        return self.name

class Incident(models.Model):
    INCIDENT_TYPES = [
        ('wildfire', 'Wildfire'),
        ('flood', 'Flood'),
        ('govt inaction/sabotage', 'Govt Inaction/Sabotage'),
    ]

    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('suspected', 'Suspected'),
    ]

    name = models.CharField(max_length=200)
    incident_type = models.CharField(max_length=50, choices=INCIDENT_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    started_at = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    geometry = JSONField()
    properties = JSONField(default=dict)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.incident_type})"

class UploadedFile(models.Model):
    file = models.FileField(upload_to='geojson_uploads/')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    incidents_added = models.IntegerField(default=0)

    def __str__(self):
        return f"Upload by {self.uploaded_by} on {self.uploaded_at}"