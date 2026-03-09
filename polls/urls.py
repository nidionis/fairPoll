from django.urls import path

from . import views

app_name = "polls"

urlpatterns = [
    path("", views.index, name="index"),
    path("home/", views.quickpoll_homepage, name="quickpoll_homepage"),
    path("quickpoll/create/", views.quickpoll_create, name="quickpoll_create"),
    path("quickpoll/join/", views.quickpoll_join, name="quickpoll_join"),
    path("quickpoll/<str:poll_id>/", views.quickpoll_voting_form, name="quickpoll_voting_form"),
    path("quickpoll/<str:poll_id>/results/", views.results, name="results"),
    path("quickpoll/<str:poll_id>/ballots/download/", views.download_ballots, name="download_ballots"),
    path("create/<int:house_id>/", views.poll_create, name="poll_create"),
    path("<str:poll_id>/", views.poll_voting_form, name="poll_voting_form"),
]
