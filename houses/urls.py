from django.urls import path

from . import views

app_name = "houses"

urlpatterns = [
    path("", views.index, name="index"),
    path("home/", views.homepage, name="houses_homepage"),
]
