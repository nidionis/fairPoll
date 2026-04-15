from django.urls import path
from . import views

app_name = 'houses'

urlpatterns = [
    path('', views.house_list, name='house_list'),
    path('user-autocomplete/', views.UserAutocomplete.as_view(), name='user-autocomplete'),
    path('create/', views.house_create, name='house_create'),
    path('<int:pk>/', views.house_detail, name='house_detail'),
    path('<int:pk>/integrate/', views.create_integration_poll, name='create_integration_poll'),
    path('<int:pk>/banish/', views.create_banishment_poll, name='create_banishment_poll'),
    path('<int:pk>/delete/', views.create_deletion_poll, name='create_deletion_poll'),
]
