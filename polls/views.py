import json
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.utils import timezone
from django.db import transaction

from .models import HousePoll, QuickPoll, HouseBallot, QuickBallot, BallotChoice, Ticket
from .forms import HousePollForm, QuickPollForm, VoteForm

User = get_user_model()


def quickpoll_list(request):
    """List all polls for a specific house"""
    from houses.models import House
    house = get_object_or_404(House, pk=house_pk)
    
    # Check if user is a member of the house
    if request.user not in house.users.all():
        raise PermissionDenied("You are not a member of this house.")
    
    polls = house.polls.all().order_by('-created_at')
    active_polls = [p for p in polls if not p.is_finished]
    archived_polls = [p for p in polls if p.is_finished]
    
    return render(request, 'polls/house_poll_list.html', {
        'house': house,
        'active_polls': active_polls,
        'archived_polls': archived_polls
    })


@login_required
def house_poll_create(request, house_pk):
    """Create a new house poll"""
    from houses.models import House
    house = get_object_or_404(House, pk=house_pk)
    
    # Check if user is a member of the house
    if request.user not in house.users.all():
        raise PermissionDenied("You are not a member of this house.")
    
    if request.method == 'POST':
        form = HousePollForm(request.POST)
        if form.is_valid():
            poll = form.save(commit=False)
            poll.house = house
            poll.creator = request.user
            poll.save()
            
            # Generate tickets if needed
            if poll.is_ticket_secured:
                tickets = poll.generate_tickets()
                messages.success(request, f"Poll created with {len(tickets)} tickets generated.")
                return redirect('polls:house_poll_tickets', poll_pk=poll.pk)
            else:
                messages.success(request, "Poll created successfully.")
                return redirect('polls:house_poll_detail', poll_pk=poll.pk)
    else:
        form = HousePollForm()
    
    return render(request, 'polls/house_poll_create.html', {
        'form': form,
        'house': house
    })


@login_required
def house_poll_detail(request, poll_pk):
    """Detail view for a house poll"""
    poll = get_object_or_404(HousePoll, pk=poll_pk)
    
    # Check if user is a member of the house
    if request.user not in poll.house.users.all():
        raise PermissionDenied("You are not a member of this house.")
    
    # Check if user has already voted
    has_voted = poll.ballots.filter(voter=request.user).exists()
    
    context = {
        'poll': poll,
        'has_voted': has_voted,
        'can_download_results': poll.is_finished
    }
    
    return render(request, 'polls/house_poll_detail.html', context)


@login_required
def house_poll_vote(request, poll_pk):
    """Vote in a house poll"""
    poll = get_object_or_404(HousePoll, pk=poll_pk)
    
    # Check if user is a member of the house
    if request.user not in poll.house.users.all():
        raise PermissionDenied("You are not a member of this house.")
    
    # Check if poll is still active
    if poll.is_finished:
        messages.error(request, "This poll has ended.")
        return redirect('polls:house_poll_detail', poll_pk=poll.pk)
    
    # Check if user has already voted
    if poll.ballots.filter(voter=request.user).exists():
        messages.error(request, "You have already voted in this poll.")
        return redirect('polls:house_poll_detail', poll_pk=poll.pk)
    
    if request.method == 'POST':
        form = VoteForm(request.POST, poll=poll)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create ballot
                    ballot = HouseBallot.objects.create(
                        poll=poll,
                        voter=None if poll.is_ticket_secured else request.user
                    )
                    
                    # Handle ticket if poll is ticket secured
                    if poll.is_ticket_secured:
                        ticket_code = form.cleaned_data.get('ticket_code')
                        ticket = get_object_or_404(Ticket, poll=poll, code=ticket_code)
                        
                        if ticket.is_used:
                            raise ValueError("This ticket has already been used.")
                        
                        ticket.is_used = True
                        ticket.save()
                        ballot.ticket = ticket
                        ballot.save()
                    
                    # Save choices
                    choices_data = form.cleaned_data['choices']
                    for option_index, rank in choices_data.items():
                        BallotChoice.objects.create(
                            house_ballot=ballot,
                            option_index=int(option_index),
                            rank=rank
                        )
                    
                    messages.success(request, "Your vote has been recorded.")
                    return redirect('polls:house_poll_detail', poll_pk=poll.pk)
                    
            except Exception as e:
                messages.error(request, f"Error recording vote: {str(e)}")
    else:
        form = VoteForm(poll=poll)
    
    return render(request, 'polls/vote.html', {
        'form': form,
        'poll': poll
    })


@login_required
def house_poll_tickets(request, poll_pk):
    """View tickets for a ticket-secured poll"""
    poll = get_object_or_404(HousePoll, pk=poll_pk)
    
    # Only creator can view tickets
    if request.user != poll.creator:
        raise PermissionDenied("Only the poll creator can view tickets.")
    
    if not poll.is_ticket_secured:
        messages.error(request, "This poll is not ticket-secured.")
        return redirect('polls:house_poll_detail', poll_pk=poll.pk)
    
    tickets = poll.tickets.all()
    
    return render(request, 'polls/house_poll_tickets.html', {
        'poll': poll,
        'tickets': tickets
    })


@login_required
def house_poll_results_json(request, poll_pk):
    """Download poll results as JSON"""
    poll = get_object_or_404(HousePoll, pk=poll_pk)
    
    # Check if user is a member of the house
    if request.user not in poll.house.users.all():
        raise PermissionDenied("You are not a member of this house.")
    
    # Only allow download if poll is finished
    if not poll.is_finished:
        messages.error(request, "Poll results are only available after the poll ends.")
        return redirect('polls:house_poll_detail', poll_pk=poll.pk)
    
    results = poll.get_results_json()
    filename = f"poll_{poll.pk}_results.json"
    
    response = HttpResponse(
        json.dumps(results, indent=2),
        content_type='application/json'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


# QuickPoll views
def quickpoll_archive(request):
    """Archive of all quick polls"""
    polls = QuickPoll.objects.all().order_by('-created_at')
    return render(request, 'polls/quickpoll_archive.html', {'polls': polls})


def quickpoll_create(request):
    """Create a new quick poll"""
    if request.method == 'POST':
        form = QuickPollForm(request.POST)
        if form.is_valid():
            poll = form.save(commit=False)
            if request.user.is_authenticated:
                poll.creator = request.user
            poll.save()
            
            messages.success(request, f"QuickPoll created! Share this ID: {poll.poll_id}")
            return redirect('polls:quickpoll_detail', poll_id=poll.poll_id)
    else:
        form = QuickPollForm()
    
    return render(request, 'polls/quickpoll_create.html', {'form': form})


def quickpoll_detail(request, poll_id):
    """Detail view for a quick poll"""
    poll = get_object_or_404(QuickPoll, poll_id=poll_id)
    
    # Check if user has already voted (if logged in)
    has_voted = False
    if request.user.is_authenticated:
        has_voted = poll.ballots.filter(voter=request.user).exists()
    
    return render(request, 'polls/quickpoll_detail.html', {
        'poll': poll,
        'has_voted': has_voted
    })


def quickpoll_vote(request, poll_id):
    """Vote in a quick poll"""
    poll = get_object_or_404(QuickPoll, poll_id=poll_id)
    
    # Check if poll is still active
    if poll.is_finished:
        messages.error(request, "This poll has ended.")
        return redirect('polls:quickpoll_detail', poll_id=poll_id)
    
    # Check if user has already voted (if logged in)
    if request.user.is_authenticated and poll.ballots.filter(voter=request.user).exists():
        messages.error(request, "You have already voted in this poll.")
        return redirect('polls:quickpoll_detail', poll_id=poll_id)
    
    if request.method == 'POST':
        form = VoteForm(request.POST, poll=poll, is_quick_poll=True)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create ballot
                    ballot = QuickBallot.objects.create(
                        poll=poll,
                        voter=request.user if request.user.is_authenticated else None
                    )
                    
                    # Save choices
                    choices_data = form.cleaned_data['choices']
                    for option_index, rank in choices_data.items():
                        BallotChoice.objects.create(
                            quick_ballot=ballot,
                            option_index=int(option_index),
                            rank=rank
                        )
                    
                    messages.success(request, "Your vote has been recorded.")
                    return redirect('polls:quickpoll_detail', poll_id=poll_id)
                    
            except Exception as e:
                messages.error(request, f"Error recording vote: {str(e)}")
    else:
        form = VoteForm(poll=poll, is_quick_poll=True)
    
    return render(request, 'polls/vote.html', {
        'form': form,
        'poll': poll,
        'is_quick_poll': True
    })
