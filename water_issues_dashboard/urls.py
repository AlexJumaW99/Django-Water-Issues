from django.urls import path
from . import views

app_name = 'water_issues_dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('api/geojson/', views.api_geojson_data, name='api_geojson'),
    path('api/search/', views.api_search, name='api_search'),
    path('upload/', views.upload_incidents, name='upload'),
    path('report/', views.report_incident_view, name='report_incident'),
]