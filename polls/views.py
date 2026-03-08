from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render

from .forms import QuickPollCreateForm, QuickPollJoinForm
from .models import QuickPoll, QuickPollProposition


def index(request):
    return HttpResponse("polls: ok")


def quickpoll_homepage(request):
    join_form = QuickPollJoinForm()
    return render(request, "polls/quickpoll_homepage.html", {"join_form": join_form})


def quickpoll_create(request):
    if request.method == "POST":
        form = QuickPollCreateForm(request.POST)
        if form.is_valid():
            propositions = form.cleaned_data["propositions_text"]

            quickpoll = form.save(commit=False)
            if request.user.is_authenticated:
                quickpoll.creator = request.user
            quickpoll.save()

            QuickPollProposition.objects.bulk_create(
                [
                    QuickPollProposition(
                        quickpoll=quickpoll,
                        text=proposition,
                        position=index,
                    )
                    for index, proposition in enumerate(propositions, start=1)
                ]
            )

            messages.success(
                request,
                f"Quick poll created successfully. Share this ID: {quickpoll.poll_id}",
            )
            return redirect("polls:quickpoll_create")
    else:
        form = QuickPollCreateForm()

    return render(request, "polls/quickpoll_create.html", {"form": form})


def quickpoll_join(request):
    if request.method != "POST":
        return redirect("polls:quickpoll_homepage")

    form = QuickPollJoinForm(request.POST)
    if not form.is_valid():
        return render(request, "polls/quickpoll_homepage.html", {"join_form": form})

    poll_id = form.cleaned_data["poll_id"]

    if not QuickPoll.objects.filter(poll_id=poll_id).exists():
        form.add_error("poll_id", "No quick poll was found with this ID.")
        return render(request, "polls/quickpoll_homepage.html", {"join_form": form})

    return redirect("polls:quickpoll_detail", poll_id=poll_id)


def quickpoll_detail(request, poll_id):
    return HttpResponse(f"quick poll participation page for {poll_id}")