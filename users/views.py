from django.http import HttpResponse
from django.shortcuts import render


def index(request):
    return HttpResponse("users: ok")


def account(request):
    return render(request, "users/account.html")


def homepage(request):
    return render(request, "users/user_homepage.html")
