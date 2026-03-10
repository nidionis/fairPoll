from django.urls import path

from . import views

app_name = "houses"

urlpatterns = [
    path("", views.index, name="index"),
    path("home/", views.homepage, name="houses_homepage"),
    path("my/", views.house_homepage, name="house_homepage"),
    path("<int:house_id>/", views.house_homepage_by_id, name="house_homepage_by_id"),
    path("<int:house_id>/archives/", views.house_archives, name="house_archives"),
    path("create/", views.create_house, name="create_house"),
]
