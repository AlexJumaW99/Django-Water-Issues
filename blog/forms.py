from django import forms
from .models import Post, Comment
from water_issues_dashboard.models import Incident

class PostForm(forms.ModelForm):
    incident = forms.ModelChoiceField(queryset=Incident.objects.all(), required=False, empty_label="Select an incident (optional)")

    class Meta:
        model = Post
        fields = ['title', 'content', 'incident']

class IncidentPostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content']

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']