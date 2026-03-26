from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.utils import timezone

User = get_user_model()


def index(request):
    return HttpResponse("users: ok")


def account(request):
    return render(request, "users/account.html")


@login_required
def homepage(request):
    pending_polls = []
    
    # Check if the user belongs to a house and find polls they haven't voted in yet
    if hasattr(request.user, 'house') and request.user.house:
        house_polls = request.user.house.polls.all()
        for poll in house_polls:
            if not poll.is_finished and not poll.ballots.filter(voter=request.user).exists():
                pending_polls.append(poll)
                
    return render(request, "home.html", {"pending_polls": pending_polls})


def user_homepage_by_id(request, user_id: int):
    viewed_user = get_object_or_404(User, id=user_id)
    return render(request, "users/user_homepage.html", {"viewed_user": viewed_user})
