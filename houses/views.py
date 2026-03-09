from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import HouseCreateForm
from .models import House

User = get_user_model()


def index(request):
    return HttpResponse("houses: ok")


def homepage(request):
    qs = House.objects.all().order_by("name")

    my_homes = []
    others = qs

    if request.user.is_authenticated:
        my_house_id = getattr(request.user, "house_id", None)
        if my_house_id:
            my_homes = list(qs.filter(id=my_house_id))
            others = qs.exclude(id=my_house_id)

    return render(
        request,
        "houses/houses_homepage.html",
        {
            "my_homes": my_homes,
            "other_homes": others,
        },
    )


@login_required
def house_homepage(request):
    """
    House homepage (for the house the current user belongs to).
    """
    if not request.user.house_id:
        messages.info(request, "You are not in a house yet.")
        return redirect("houses:houses_homepage")

    house = request.user.house

    polls_to_do = []
    pending_polls = []
    
    for poll in house.polls.all():
        if not poll.is_finished():
            if poll.is_ticket_secured:
                polls_to_do.append(poll)
            else:
                if poll.votes.filter(user=request.user).exists():
                    pending_polls.append(poll)
                else:
                    polls_to_do.append(poll)

    members = house.members.all().order_by("username")

    return render(
        request,
        "houses/house_homepage.html",
        {
            "house": house,
            "polls_to_do": polls_to_do,
            "pending_polls": pending_polls,
            "members": members,
            "archives_url": "#",
        },
    )


@login_required
def house_homepage_by_id(request, house_id: int):
    """
    House homepage (for a specific house).
    """
    house = House.objects.get(id=house_id)

    polls_to_do = []
    pending_polls = []
    
    for poll in house.polls.all():
        if not poll.is_finished():
            if poll.is_ticket_secured:
                polls_to_do.append(poll)
            else:
                if request.user.is_authenticated and poll.votes.filter(user=request.user).exists():
                    pending_polls.append(poll)
                else:
                    polls_to_do.append(poll)

    members = house.members.all().order_by("username")

    return render(
        request,
        "houses/house_homepage.html",
        {
            "house": house,
            "polls_to_do": polls_to_do,
            "pending_polls": pending_polls,
            "members": members,
            "archives_url": "#",
        },
    )


@login_required
def create_house(request):
    # Quota rule: free -> 1/day, paid -> 10/day
    daily_limit = 10 if getattr(request.user, "plan", "free") == "paid" else 1

    today = timezone.localdate()
    created_today = House.objects.filter(creator=request.user, created_at__date=today).count()
    if created_today >= daily_limit:
        messages.error(request, f"Daily limit reached: {daily_limit} house(s) per day for your plan.")
        return redirect("houses:houses_homepage")

    if request.method == "POST":
        form = HouseCreateForm(request.POST, request_user=request.user)
        if form.is_valid():
            house = form.save()

            members = form.cleaned_data.get("members")
            if members:
                User.objects.filter(id__in=members.values_list("id", flat=True)).update(house=house)

            if request.user.house_id != house.id:
                request.user.house = house
                request.user.save(update_fields=["house"])

            messages.success(request, "House created successfully.")
            return redirect("houses:houses_homepage")
    else:
        form = HouseCreateForm(request_user=request.user)

    return render(request, "houses/create_house.html", {"form": form})
