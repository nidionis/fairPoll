from django.urls import path
from . import views

urlpatterns = [
    # URL pour créer un scrutin lié à une maison spécifique
    path('house/<int:house_id>/create/', views.PollCreateView.as_view(), name='poll_create'),
    path('mes-scrutins/', views.UserPollsListView.as_view(), name='user_polls'),
    path('<int:pk>/', views.PollDetailView.as_view(), name='poll_detail'),
    path('<int:pk>/vote/', views.poll_vote, name='poll_vote'),
    
    # Add the missing URLs here
    path('<int:pk>/results/download/', views.PollResultsDownloadView.as_view(), name='poll_results_download'),
    path('<int:pk>/keys/download/', views.PollKeysDownloadView.as_view(), name='poll_keys_download'),
]