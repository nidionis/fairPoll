from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("", views.index, name="index"),
    path("account/", views.account, name="account"),
    path("profile/", views.profile_update, name="profile_update"),
    path("home/", views.homepage, name="user_homepage"),
    path("<int:user_id>/", views.user_homepage_by_id, name="user_homepage_by_id"),
]
