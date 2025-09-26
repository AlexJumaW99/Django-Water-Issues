from django.contrib import admin
from .models import Municipality, Park, Incident, UploadedFile

@admin.register(Municipality)
class MunicipalityAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'population_2021']
    list_filter = ['status']
    search_fields = ['name']

@admin.register(Park)
class ParkAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'management']
    search_fields = ['name', 'location']

@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ['name', 'incident_type', 'status', 'started_at', 'uploaded_by']
    list_filter = ['incident_type', 'status']
    search_fields = ['name', 'description']

@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ['uploaded_by', 'uploaded_at', 'processed', 'incidents_added']
    list_filter = ['processed', 'uploaded_at']