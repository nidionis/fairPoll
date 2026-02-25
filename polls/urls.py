from django.urls import path
from . import views

urlpatterns = [
    # URL pour créer un scrutin lié à une maison spécifique
    path('house/<int:house_id>/create/', views.PollCreateView.as_view(), name='poll_create'),
    path('<int:pk>/', views.PollDetailView.as_view(), name='poll_detail'),
    path('<int:pk>/update/', views.PollUpdateView.as_view(), name='poll_update'),
    path('<int:pk>/delete/', views.PollDeleteView.as_view(), name='poll_delete'),
]