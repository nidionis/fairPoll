from django.urls import path
from . import views

urlpatterns = [
    path('houses/', views.HouseListView.as_view(), name='house-list'),
    path('houses/<int:pk>/', views.HouseDetailView.as_view(), name='house-detail'),
    path('houses/create/', views.HouseCreateView.as_view(), name='house-create'),
    path('houses/<int:pk>/update/', views.HouseUpdateView.as_view(), name='house-update'),
    path('houses/<int:pk>/delete/', views.HouseDeleteView.as_view(), name='house-delete'),
    
    # Nouvelles routes pour l'intégration et l'invitation
    path('houses/<int:pk>/request-integration/', views.RequestIntegrationView.as_view(), name='house-request-integration'),
    path('houses/<int:house_pk>/invite/<int:user_pk>/', views.InviteUserView.as_view(), name='house-invite-user'),
]