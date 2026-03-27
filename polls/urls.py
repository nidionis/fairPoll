from django.urls import path
from . import views

app_name = 'polls'

urlpatterns = [
    path('house/<int:house_pk>/create/', views.house_poll_create, name='house_poll_create'),
    path('house_poll/<str:external_id>/', views.house_poll_detail, name='house_poll_detail'),
    path('house_poll/<str:external_id>/vote/', views.house_poll_vote, name='house_poll_vote'),
    path('house_poll/<str:external_id>/results/', views.house_poll_results, name='house_poll_results'),
    path('house_poll/<str:external_id>/export/', views.house_poll_export, name='house_poll_export'),
    
    path('quickpoll/create/', views.quickpoll_create, name='quickpoll_create'),
    path('quickpoll/archive/', views.quickpoll_archive, name='quickpoll_archive'),
    path('quickpoll/<str:external_id>/', views.quickpoll_detail, name='quickpoll_detail'),
    path('quickpoll/<str:external_id>/vote/', views.quickpoll_vote, name='quickpoll_vote'),
    path('quickpoll/<str:external_id>/results/', views.quickpoll_results, name='quickpoll_results'),
    path('quickpoll/<str:external_id>/export/', views.quickpoll_export, name='quickpoll_export'),
    path('quickpoll/<str:external_id>/tickets/', views.quickpoll_tickets_export, name='quickpoll_tickets_export'),
    path('poll/join/', views.poll_join, name='poll_join'),
]
