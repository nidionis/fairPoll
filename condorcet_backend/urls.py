from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path, reverse
from django.views.generic import TemplateView
from django.contrib.sitemaps import Sitemap
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from two_factor.urls import urlpatterns as tf_urls


def root_home(request):
    if request.user.is_authenticated:
        return redirect("users:user_homepage")
    return TemplateView.as_view(template_name="home.html")(request)


class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = 'weekly'

    def items(self):
        return ['home', 'about']

    def location(self, item):
        return reverse(item)


sitemaps = {
    'static': StaticViewSitemap,
}


def robots_txt(request):
    lines = [
        "User-Agent: *",
        "Disallow: /admin/",
        "Disallow: /account/",
        "Disallow: /users/",
        "Disallow: /houses/create/",
        "Disallow: /polls/*/create/",
        "Disallow: /polls/*/export/",
        "Disallow: /polls/*/tickets/",
        "Allow: /",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}"
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def robot_redirect(request):
    return redirect("robots_txt", permanent=True)


urlpatterns = [
    path("", root_home, name="home"),
    path("about/", TemplateView.as_view(template_name="about.html"), name="about"),
    path("admin/", admin.site.urls),
    path("account/", include("allauth.urls")),
    path("", include((tf_urls[0], "two_factor"), namespace="two_factor")),
    path("users/", include("users.urls")),
    path("houses/", include("houses.urls")),
    path("polls/", include("polls.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("robot.txt", robot_redirect),
]