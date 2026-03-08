from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render, get_object_or_404

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

    return redirect("polls:quickpoll_voting_form", poll_id=poll_id)


def quickpoll_voting_form(request, poll_id):
    poll = get_object_or_404(QuickPoll, poll_id=poll_id)

    # Check if the poll is finished
    if poll.is_finished():
        messages.error(request, "This poll is already finished.")
        return redirect("polls:quickpoll_homepage")

    # Check if the client has already voted using session
    voted_polls = request.session.get("voted_quickpolls", [])
    if poll_id in voted_polls:
        messages.error(request, "You have already voted in this poll.")
        return redirect("polls:quickpoll_homepage")

    propositions = poll.propositions.all()

    if request.method == "POST":
        ordered_ids_string = request.POST.get("ordered_propositions")
        
        if not ordered_ids_string:
            messages.error(request, "Invalid vote data submitted.")
            return redirect("polls:quickpoll_voting_form", poll_id=poll_id)

        # Parse the comma-separated string back into a list of IDs
        ordered_ids = ordered_ids_string.split(",")
        
        # Here you would typically save the vote using the ordered_ids
        # For now, we will just register that the user voted.
        
        poll.participants_voted_count += 1
        poll.save()

        voted_polls.append(poll_id)
        request.session["voted_quickpolls"] = voted_polls
        
        messages.success(request, "Your vote has been successfully registered.")
        return redirect("polls:quickpoll_homepage")

    context = {
        "poll": poll,
        "propositions": propositions,
    }
    return render(request, "polls/quickpoll_voting_form.html", context)