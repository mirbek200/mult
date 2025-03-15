from django.urls import path
from .views import VideoGenerationView

urlpatterns = [
    path('generate_video/', VideoGenerationView.as_view(), name='generate_video'),
]
