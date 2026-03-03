from django.http import HttpResponse


def index(request):
    return HttpResponse("houses: ok")


def homepage(request):
    return HttpResponse("houses homepage: ok")
