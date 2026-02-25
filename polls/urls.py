from django.urls import path
from . import views

urlpatterns = [
    # URL pour créer un scrutin lié à une maison spécifique
    path('house/<int:house_id>/create/', views.PollCreateView.as_view(), name='poll_create'),
]