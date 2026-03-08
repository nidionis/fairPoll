from django.urls import path

from . import views

app_name = "polls"

urlpatterns = [
    path("", views.index, name="index"),
    path("home/", views.quickpoll_homepage, name="quickpoll_homepage"),
    path("quickpoll/create/", views.quickpoll_create, name="quickpoll_create"),
    path("quickpoll/join/", views.quickpoll_join, name="quickpoll_join"),
    path("quickpoll/<str:poll_id>/", views.quickpoll_detail, name="quickpoll_detail"),
]
