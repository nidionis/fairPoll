from django.http import HttpResponse


def index(request):
    return HttpResponse("polls: ok")


def homepage(request):
    return HttpResponse("polls homepage: ok")


def quickpoll_create(request):
    return HttpResponse("quickpoll create: ok")
