from django.urls import path
from . import views

urlpatterns = [
    path('houses/', views.HouseListView.as_view(), name='house-list'),
    path('houses/<int:pk>/', views.HouseDetailView.as_view(), name='house-detail'),
    path('houses/create/', views.HouseCreateView.as_view(), name='house-create'),
    path('houses/<int:pk>/update/', views.HouseUpdateView.as_view(), name='house-update'),
    path('houses/<int:pk>/delete/', views.HouseDeleteView.as_view(), name='house-delete'),
]