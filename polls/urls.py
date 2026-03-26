from django.urls import path
from . import views

app_name = 'polls'

urlpatterns = [
    # House polls
    path('house/<int:house_pk>/', views.house_poll_list, name='house_poll_list'),
    path('house/<int:house_pk>/create/', views.house_poll_create, name='house_poll_create'),
    path('house-poll/<int:poll_pk>/', views.house_poll_detail, name='house_poll_detail'),
    path('house-poll/<int:poll_pk>/vote/', views.house_poll_vote, name='house_poll_vote'),
    path('house-poll/<int:poll_pk>/tickets/', views.house_poll_tickets, name='house_poll_tickets'),
    path('house-poll/<int:poll_pk>/results.json', views.house_poll_results_json, name='house_poll_results_json'),

    # Quick polls
    path('quick/', views.quickpoll_archive, name='quickpoll_archive'),
    path('quick/create/', views.quickpoll_create, name='quickpoll_create'),
    path('quick/<str:poll_id>/', views.quickpoll_detail, name='quickpoll_detail'),
    path('quick/<str:poll_id>/vote/', views.quickpoll_vote, name='quickpoll_vote'),
]
