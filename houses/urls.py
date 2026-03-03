from django.urls import path

from . import views

app_name = "houses"

urlpatterns = [
    path("", views.index, name="index"),
]
