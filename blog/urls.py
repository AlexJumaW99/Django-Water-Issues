from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('blog/', views.home, name='blog-home'),
    path('about/', views.about, name='blog-about'),
    path('post/<int:post_id>/', views.post, name='blog-post'),
    path('profile/<int:user_id>/', views.profile, name='blog-profile'),
    path('post/<int:post_id>/comment/', views.post, name='add-comment'),
    path('like_post/', views.like_post, name='like-post'),
    path('incident/<int:incident_id>/discussion/', views.incident_discussion, name='incident-discussion'),
]