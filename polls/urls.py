from django.urls import path

from . import views

app_name = "polls"

urlpatterns = [
    path("", views.index, name="index"),
    path("home/", views.homepage, name="polls_homepage"),
    path("quickpoll/create/", views.quickpoll_create, name="quickpoll_create"),
]
