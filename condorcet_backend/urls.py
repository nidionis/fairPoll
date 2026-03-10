from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path
from django.views.generic import TemplateView
from two_factor.urls import urlpatterns as tf_urls


def root_home(request):
    if request.user.is_authenticated:
        return redirect("users:user_homepage")
    return TemplateView.as_view(template_name="home.html")(request)


urlpatterns = [
    path("", root_home, name="home"),
    path("admin/", admin.site.urls),
    path("account/", include("allauth.urls")),
    path("", include((tf_urls[0], "two_factor"), namespace="two_factor")),
    path("users/", include("users.urls")),
    path("houses/", include("houses.urls")),
    path("polls/", include("polls.urls")),
]