from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

User = get_user_model()


def index(request):
    return HttpResponse("users: ok")


def account(request):
    return render(request, "users/account.html")


def homepage(request):
    return render(request, "users/user_homepage.html")


def user_homepage_by_id(request, user_id: int):
    viewed_user = get_object_or_404(User, id=user_id)
    return render(request, "users/user_homepage.html", {"viewed_user": viewed_user})
