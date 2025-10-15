from django.core.management.base import BaseCommand
from water_issues_dashboard.models import Municipality, Park, Incident
import json
import os
from datetime import datetime
from django.core.files.base import ContentFile
import requests

class Command(BaseCommand):
    help = 'Load initial data from GeoJSON files'

    def add_arguments(self, parser):
        parser.add_argument('--data-dir', type=str, help='Path to data directory', default='data')

    def handle(self, *args, **options):
        data_dir = options['data_dir']

        # Load municipalities
        self.load_geojson_data(
            os.path.join(data_dir, 'mb_with_winnipeg.geojson'),
            Municipality,
            self.process_municipality
        )

        # Load parks
        self.load_geojson_data(
            os.path.join(data_dir, 'Manitoba_Parks_full.geojson'),
            Park,
            self.process_park
        )

        # Load incidents
        self.load_geojson_data(
            os.path.join(data_dir, 'incidents_dummy.geojson'),
            Incident,
            self.process_incident
        )

    def load_geojson_data(self, filepath, model_class, processor_func):
        if not os.path.exists(filepath):
            self.stdout.write(self.style.ERROR(f"File not found: {filepath}"))
            return

        with open(filepath, 'r') as f:
            data = json.load(f)

        count = 0
        for feature in data.get('features', []):
            obj = processor_func(feature)
            if obj:
                if model_class == Incident:
                    count += 1
                else:
                    obj.save()
                    count += 1


        self.stdout.write(self.style.SUCCESS(f"Loaded {count} {model_class.__name__} records from {filepath}"))

    def process_municipality(self, feature):
        props = feature.get('properties', {})
        return Municipality(
            name=props.get('MUNI_NAME') or props.get('name', ''),
            status=props.get('MUNI_STATU') or props.get('status', ''),
            population_2021=int(props.get('population_2021', 0) or 0),
            geometry=feature.get('geometry', {}),
            properties=props
        )

    def process_park(self, feature):
        props = feature.get('properties', {})
        return Park(
            name=props.get('NAME_E', ''),
            location=props.get('LOC_E', ''),
            management=props.get('MGMT_E', ''),
            owner=props.get('OWNER_E', ''),
            park_class=props.get('PRK_CLSS', ''),
            url=props.get('URL', ''),
            geometry=feature.get('geometry', {}),
            properties=props
        )

    def process_incident(self, feature):
        props = feature.get('properties', {})
        
        incident_type = props.get('type', 'flood').lower()
        
        valid_types = [
            'flood', 'drought', 'algal bloom', 'contaminated water',
            'hydroelectric disruption', 'invasive species', 'declining fish population'
        ]
        
        if incident_type not in valid_types:
            incident_type = 'flood'
        
        incident = Incident(
            name=props.get('name', ''),
            incident_type=incident_type,
            status=props.get('status', 'suspected'),
            description=props.get('description', ''),
            geometry=feature.get('geometry', {}),
            properties=props
        )
        if props.get('started_at'):
            try:
                date_string = props['started_at'].split('T')[0]
                incident.started_at = datetime.strptime(date_string, '%Y-%m-%d').date()
            except (ValueError, TypeError, IndexError):
                pass
        
        # --- New Image URL Handling Logic ---
        image_url = props.get('image_url')
        if image_url:
            try:
                response = requests.get(image_url, stream=True)
                response.raise_for_status()  # Raise an exception for bad status codes

                # Get the filename from the URL
                filename = image_url.split('/')[-1].split('?')[0]

                # Create a ContentFile from the downloaded content
                image_content = ContentFile(response.content)

                # Save the image to the Incident model
                incident.image.save(filename, image_content, save=True)

            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.WARNING(f"Could not download image from {image_url}: {e}"))
        
        incident.save()
        return incident