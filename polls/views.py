from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import QuickPollCreateForm, QuickPollJoinForm, PollCreateForm
from .models import QuickPoll, Poll, Proposition, Vote, Ticket, generate_poll_id


def index(request):
    return render(request, "polls/homepage.html")


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

            Proposition.objects.bulk_create(
                [
                    Proposition(
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
            return redirect("polls:quickpoll_voting_form", poll_id=quickpoll.poll_id)
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
        messages.info(request, "This poll is finished. Here are the results.")
        return redirect("polls:results", poll_id=poll_id)

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
        
        # Save the vote
        Vote.objects.create(
            quickpoll=poll,
            ordered_propositions_ids=ordered_ids_string
        )
        
        poll.participants_voted_count += 1
        poll.save()

        voted_polls.append(poll_id)
        request.session["voted_quickpolls"] = voted_polls
        
        messages.success(request, "Your vote has been successfully registered.")
        
        if poll.is_finished():
            return redirect("polls:results", poll_id=poll_id)
        return redirect("polls:quickpoll_homepage")

    context = {
        "poll": poll,
        "propositions": propositions,
    }
    return render(request, "polls/quickpoll_voting_form.html", context)


def results(request, poll_id):
    poll = get_object_or_404(QuickPoll, poll_id=poll_id)

    if not poll.is_finished():
        messages.warning(request, "The poll is not finished yet.")
        return redirect("polls:quickpoll_voting_form", poll_id=poll_id)

    propositions = poll.propositions.all()
    votes = poll.votes.all()

    # Simple statistics: Count first choices
    first_choice_counts = {prop.id: 0 for prop in propositions}
    for vote in votes:
        ordered_ids = vote.get_ordered_propositions()
        if ordered_ids:
            first_choice = ordered_ids[0]
            if first_choice in first_choice_counts:
                first_choice_counts[first_choice] += 1

    # Attach stats to propositions
    stats = []
    for prop in propositions:
        stats.append({
            "text": prop.text,
            "first_choices": first_choice_counts[prop.id]
        })
        
    stats.sort(key=lambda x: x["first_choices"], reverse=True)

    context = {
        "poll": poll,
        "stats": stats,
        "total_votes": votes.count(),
    }
    return render(request, "polls/results.html", context)


def download_ballots(request, poll_id):
    poll = get_object_or_404(QuickPoll, poll_id=poll_id)

    if not poll.is_finished():
        return JsonResponse({"error": "Poll is not finished yet."}, status=403)

    votes = poll.votes.all()
    propositions_dict = {prop.id: prop.text for prop in poll.propositions.all()}
    ballots = []

    for vote in votes:
        readable_vote = [propositions_dict.get(pid, str(pid)) for pid in vote.get_ordered_propositions()]
        ballots.append({
            "secret_ID": "none",
            "vote": readable_vote
        })

    response = JsonResponse(ballots, safe=False)
    response['Content-Disposition'] = f'attachment; filename="counting_ballots_{poll.poll_id}.json"'
    return response

@login_required
def poll_create(request, house_id):
    from houses.models import House
    house = get_object_or_404(House, id=house_id)
    
    if request.method == "POST":
        form = PollCreateForm(request.POST)
        if form.is_valid():
            propositions = form.cleaned_data["propositions_text"]
            
            poll = form.save(commit=False)
            poll.creator = request.user
            poll.house = house
            poll.save()

            # Create Propositions
            Proposition.objects.bulk_create([
                Proposition(poll=poll, text=prop, position=idx)
                for idx, prop in enumerate(propositions, start=1)
            ])

            # Generate Tickets if secured
            if poll.is_ticket_secured:
                member_count = house.members.count()
                tickets = []
                for _ in range(member_count):
                    tickets.append(Ticket(poll=poll, code=generate_poll_id()))
                Ticket.objects.bulk_create(tickets)

            messages.success(request, f"Poll created! ID: {poll.poll_id}")
            return redirect("polls:poll_voting_form", poll_id=poll.poll_id)
    else:
        # Default duration for normal poll is 20 min
        form = PollCreateForm(initial={"duration_minutes": 20})

    return render(request, "polls/poll_create.html", {"form": form, "house": house})


def poll_voting_form(request, poll_id):
    poll = get_object_or_404(Poll, poll_id=poll_id)

    # 1. Check if the poll is finished
    if poll.is_finished():
        messages.info(request, "This poll is finished.")
        return redirect("polls:results", poll_id=poll_id)

    # 2. Security Checks
    if not poll.is_ticket_secured:
        # --- Connection Secured ---
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to vote in this poll.")
            # Redirect to login page, optionally passing the current URL as 'next'
            return redirect(f"/account/login/?next={request.path}")
        
        # Check if user already voted
        if Vote.objects.filter(poll=poll, user=request.user).exists():
            messages.error(request, "You have already voted in this poll.")
            return redirect("polls:index") # Adjust redirect as needed
    
    propositions = poll.propositions.all()

    # 3. Handle the Vote Submission
    if request.method == "POST":
        ordered_ids_string = request.POST.get("ordered_propositions")
        
        if not ordered_ids_string:
            messages.error(request, "Invalid vote data submitted.")
            return redirect("polls:poll_voting_form", poll_id=poll_id)

        # If it's ticket secured, validate the ticket provided in the form
        ticket_code = request.POST.get("ticket_code")
        used_ticket = None
        
        if poll.is_ticket_secured:
            if not ticket_code:
                messages.error(request, "A ticket code is required for this poll.")
                return redirect("polls:poll_voting_form", poll_id=poll_id)
            
            try:
                # Find the ticket for this specific poll
                used_ticket = Ticket.objects.get(poll=poll, code=ticket_code)
                if used_ticket.is_used:
                    messages.error(request, "This ticket has already been used.")
                    return redirect("polls:poll_voting_form", poll_id=poll_id)
            except Ticket.DoesNotExist:
                messages.error(request, "Invalid ticket code.")
                return redirect("polls:poll_voting_form", poll_id=poll_id)

        # Save the vote
        vote = Vote(
            poll=poll,
            ordered_propositions_ids=ordered_ids_string
        )
        
        # Attach the user if it's connection-secured
        if not poll.is_ticket_secured:
            vote.user = request.user
            
        vote.save()

        # Mark ticket as used if applicable
        if used_ticket:
            used_ticket.is_used = True
            used_ticket.save()

        # Update poll count
        poll.participants_voted_count += 1
        poll.save()
    
        messages.success(request, "Your vote has been successfully registered.")
        return redirect("polls:index") # Adjust redirect as needed

    context = {
        "poll": poll,
        "propositions": propositions,
    }
    return render(request, "polls/poll_voting_form.html", context)