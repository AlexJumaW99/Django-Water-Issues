# Blog/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('blog/', views.home, name='blog-home'),
    path('about/', views.about, name='blog-about'),
    path('post/<int:post_id>/', views.post, name='blog-post'),
    path('profile/<int:user_id>/', views.profile, name='blog-profile')
    # Add more URL patterns for your app here
]