from django.core.management.base import BaseCommand
from water_issues_dashboard.models import Municipality, Park, Incident
import json
import os

class Command(BaseCommand):
    help = 'Load initial data from GeoJSON files'
    
    def add_arguments(self, parser):
        parser.add_argument('--data-dir', type=str, help='Path to data directory')
    
    def handle(self, *args, **options):
        data_dir = options['data_dir'] or 'data'
        
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
            self.stdout.write(f"File not found: {filepath}")
            return
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        count = 0
        for feature in data.get('features', []):
            obj = processor_func(feature)
            if obj:
                obj.save()
                count += 1
        
        self.stdout.write(f"Loaded {count} {model_class.__name__} records")
    
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
        return Incident(
            name=props.get('name', ''),
            incident_type=props.get('type', 'wildfire'),
            status=props.get('status', 'suspected'),
            description=props.get('description', ''),
            geometry=feature.get('geometry', {}),
            properties=props
        )