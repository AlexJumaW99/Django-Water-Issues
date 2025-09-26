from django import forms
from .models import UploadedFile

class IncidentUploadForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={
                'accept': '.json,.geojson',
                'class': 'form-control'
            })
        }
    
    def clean_file(self):
        file = self.cleaned_data['file']
        if file:
            if not file.name.endswith(('.json', '.geojson')):
                raise forms.ValidationError('Only JSON and GeoJSON files are allowed.')
            
            # Check file size (limit to 10MB)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File size must be under 10MB.')
        
        return file