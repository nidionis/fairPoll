from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("", views.index, name="index"),
    path("account/", views.account, name="account"),
    path("home/", views.homepage, name="user_homepage"),
]
