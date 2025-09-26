from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Municipality, Park, Incident, UploadedFile
from .forms import IncidentUploadForm
import json
import os
from datetime import datetime

@login_required
def dashboard_home(request):
    """Main dashboard view"""
    # Get filter parameters
    status_filters = {
        'city': request.GET.get('statusCity', 'true') == 'true',
        'town': request.GET.get('statusTown', 'true') == 'true',
        'rm': request.GET.get('statusRM', 'true') == 'true',
    }
    
    pop_min = int(request.GET.get('popMin', 0))
    pop_max = int(request.GET.get('popMax', 1000000))
    
    incident_filters = {
        'wildfires': request.GET.get('showWildfires', 'true') == 'true',
        'floods': request.GET.get('showFloods', 'true') == 'true',
        'confirmed': request.GET.get('statusConfirmed', 'true') == 'true',
        'suspected': request.GET.get('statusSuspected', 'true') == 'true',
    }
    
    show_parks = request.GET.get('showParks', 'true') == 'true'
    
    # Build queryset for municipalities
    muni_query = Municipality.objects.all()
    if not status_filters['city']:
        muni_query = muni_query.exclude(status='city')
    if not status_filters['town']:
        muni_query = muni_query.exclude(status='town')
    if not status_filters['rm']:
        muni_query = muni_query.exclude(status__in=['rm', 'rural municipality'])
    
    municipalities = muni_query.filter(
        population_2021__gte=pop_min,
        population_2021__lte=pop_max
    )
    
    # Build queryset for incidents
    incident_query = Incident.objects.all()
    incident_types = []
    if incident_filters['wildfires']:
        incident_types.append('wildfire')
    if incident_filters['floods']:
        incident_types.append('flood')
    
    incident_statuses = []
    if incident_filters['confirmed']:
        incident_statuses.append('confirmed')
    if incident_filters['suspected']:
        incident_statuses.append('suspected')
    
    incidents = incident_query.filter(
        incident_type__in=incident_types,
        status__in=incident_statuses
    )
    
    # Get parks if needed
    parks = Park.objects.all() if show_parks else Park.objects.none()
    
    context = {
        'municipalities': municipalities,
        'incidents': incidents,
        'parks': parks,
        'municipality_count': municipalities.count(),
        'total_population': sum(m.population_2021 for m in municipalities),
        'wildfire_count': incidents.filter(incident_type='wildfire').count(),
        'flood_count': incidents.filter(incident_type='flood').count(),
        'park_count': parks.count(),
        'filters': {
            'status': status_filters,
            'pop_min': pop_min,
            'pop_max': pop_max,
            'incidents': incident_filters,
            'show_parks': show_parks,
        }
    }
    
    return render(request, 'water_issues_dashboard/dashboard.html', context)

def api_geojson_data(request):
    """API endpoint to return GeoJSON data for the map"""
    data_type = request.GET.get('type', 'all')
    
    response_data = {
        'municipalities': {
            'type': 'FeatureCollection',
            'features': []
        },
        'incidents': {
            'type': 'FeatureCollection', 
            'features': []
        },
        'parks': {
            'type': 'FeatureCollection',
            'features': []
        }
    }
    
    if data_type in ['all', 'municipalities']:
        for muni in Municipality.objects.all():
            feature = {
                'type': 'Feature',
                'geometry': muni.geometry,
                'properties': {
                    'name': muni.name,
                    'status': muni.status,
                    'population_2021': muni.population_2021,
                    **muni.properties
                }
            }
            response_data['municipalities']['features'].append(feature)
    
    if data_type in ['all', 'incidents']:
        for incident in Incident.objects.all():
            feature = {
                'type': 'Feature',
                'geometry': incident.geometry,
                'properties': {
                    'id': incident.id,
                    'name': incident.name,
                    'type': incident.incident_type,
                    'status': incident.status,
                    'started_at': incident.started_at.isoformat() if incident.started_at else None,
                    'description': incident.description,
                    **incident.properties
                }
            }
            response_data['incidents']['features'].append(feature)
    
    if data_type in ['all', 'parks']:
        for park in Park.objects.all():
            feature = {
                'type': 'Feature',
                'geometry': park.geometry,
                'properties': {
                    'NAME_E': park.name,
                    'LOC_E': park.location,
                    'MGMT_E': park.management,
                    'OWNER_E': park.owner,
                    'PRK_CLSS': park.park_class,
                    'URL': park.url,
                    **park.properties
                }
            }
            response_data['parks']['features'].append(feature)
    
    return JsonResponse(response_data)


@login_required
def upload_incidents(request):
    """Handle file upload for incidents"""
    if request.method == 'POST':
        form = IncidentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.save(commit=False)
            uploaded_file.uploaded_by = request.user
            uploaded_file.save()
            
            # Process the uploaded file
            try:
                result = process_geojson_file(uploaded_file)
                uploaded_file.processed = True
                uploaded_file.incidents_added = result['added']
                uploaded_file.save()
                
                return JsonResponse({
                    'success': True,
                    'added': result['added'],
                    'duplicates': result['duplicates'],
                    'total': Incident.objects.count()
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'Error processing file: {str(e)}'
                })
    else:
        form = IncidentUploadForm()
    
    return render(request, 'water_issues_dashboard/upload.html', {'form': form})

def process_geojson_file(uploaded_file):
    """Process uploaded GeoJSON file and create incidents"""
    with open(uploaded_file.file.path, 'r') as f:
        data = json.load(f)
    
    if data.get('type') != 'FeatureCollection' or 'features' not in data:
        raise ValueError('Invalid GeoJSON format')
    
    added = 0
    duplicates = 0
    
    for feature in data['features']:
        props = feature.get('properties', {})
        name = props.get('name', '').strip()
        incident_type = props.get('type', '').strip().lower()
        
        # Simple duplicate check
        if Incident.objects.filter(name=name, incident_type=incident_type).exists():
            duplicates += 1
            continue
        
        # Create new incident
        incident = Incident(
            name=name,
            incident_type=incident_type,
            status=props.get('status', 'suspected'),
            description=props.get('description', ''),
            geometry=feature.get('geometry', {}),
            properties=props,
            uploaded_by=uploaded_file.uploaded_by
        )
        
        # ** FIX STARTS HERE **
        # Parse date if provided, handling full ISO 8601 timestamps
        if props.get('started_at'):
            try:
                # Extract just the date part (e.g., '2025-08-21') from the timestamp
                date_string = props['started_at'].split('T')[0]
                incident.started_at = datetime.strptime(date_string, '%Y-%m-%d').date()
            except (ValueError, TypeError, IndexError):
                # Silently pass if the date format is invalid or can't be split
                pass
        # ** FIX ENDS HERE **
        
        incident.save()
        added += 1
    
    return {'added': added, 'duplicates': duplicates}

def api_search(request):
    """API endpoint for search functionality"""
    query = request.GET.get('q', '').lower().strip()
    if not query:
        return JsonResponse({'results': []})
    
    results = []
    
    # Search municipalities
    munis = Municipality.objects.filter(name__icontains=query)[:5]
    for muni in munis:
        results.append({
            'label': f"{muni.status.title()} of {muni.name}, MB",
            'type': muni.status.title(),
            'geometry': muni.geometry
        })
    
    # Search parks
    parks = Park.objects.filter(name__icontains=query)[:5]
    for park in parks:
        results.append({
            'label': f"{park.name} (Park)",
            'type': 'Park',
            'geometry': park.geometry
        })
    
    # Search incidents
    incidents = Incident.objects.filter(name__icontains=query)[:5]
    for incident in incidents:
        results.append({
            'label': f"{incident.name} ({incident.incident_type.title()})",
            'type': incident.incident_type.title(),
            'geometry': incident.geometry
        })
    
    return JsonResponse({'results': results})