from django.urls import path
from . import views

urlpatterns = [
    path('houses/', views.HouseListView.as_view(), name='house-list'),
    path('houses/<int:pk>/', views.HouseDetailView.as_view(), name='house-detail'),
    path('houses/create/', views.HouseCreateView.as_view(), name='house-create'),
    path('houses/<int:pk>/update/', views.HouseUpdateView.as_view(), name='house-update'),
    path('houses/<int:pk>/delete/', views.HouseDeleteView.as_view(), name='house-delete'),
    
    # Route pour l'archive des scrutins d'une maison
    path('houses/<int:pk>/polls/archive/', views.HousePollsArchiveView.as_view(), name='house-polls-archive'),

    # Nouvelles routes pour l'intégration et l'invitation
    path('houses/<int:pk>/request-integration/', views.RequestIntegrationView.as_view(), name='house-request-integration'),
    path('houses/<int:house_pk>/invite/<int:user_pk>/', views.InviteUserView.as_view(), name='house-invite-user'),
    
    # Nouvelles routes pour le bannissement
    path('houses/<int:house_pk>/banish-user/<int:user_pk>/', views.BanishUserView.as_view(), name='house-banish-user'),
    path('houses/<int:house_pk>/banish-house/<int:target_house_pk>/', views.BanishHouseView.as_view(), name='house-banish-house'),
]