from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db import models
from django import forms
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
from .models import HousePoll, QuickPoll, Ticket, Ballot
from .forms import HousePollForm, QuickPollForm, VoteForm
from polls.models import HousePoll
from houses.models import House

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def calculate_condorcet(poll):
    """
    Calculates Condorcet head-to-head match-ups for the given poll.
    """
    options = poll.options
    # Initialize matrix: matrix[A][B] = number of times A beats B
    matrix = {opt1: {opt2: 0 for opt2 in options} for opt1 in options}
    
    for ballot in poll.ballots.all():
        if not isinstance(ballot.choices, dict):
            continue
            
        choices = ballot.choices
        for i, opt1 in enumerate(options):
            for j, opt2 in enumerate(options):
                if i == j:
                    continue
                rank1 = choices.get(opt1)
                rank2 = choices.get(opt2)
                
                # If a rank is missing, treat it as worst possible rank (infinity)
                val1 = float('inf') if rank1 is None else float(rank1)
                val2 = float('inf') if rank2 is None else float(rank2)
                
                if val1 < val2:
                    matrix[opt1][opt2] += 1

    wins_count = {opt: 0 for opt in options}
    losses_count = {opt: 0 for opt in options}
    ties_count = {opt: 0 for opt in options}
    
    for opt1 in options:
        for opt2 in options:
            if opt1 == opt2:
                continue
            wins = matrix[opt1][opt2]
            losses = matrix[opt2][opt1]
            if wins > losses:
                wins_count[opt1] += 1
            elif wins < losses:
                losses_count[opt1] += 1
            else:
                ties_count[opt1] += 1

    # A Condorcet winner beats every other option
    winners = [opt for opt in options if wins_count[opt] == len(options) - 1]
    
    # Sort options by preference
    # 1. Copeland score (Wins - Losses) descending
    # 2. Least losses ascending
    # 3. Original order in poll.options
    sorted_options = sorted(
        options,
        key=lambda opt: (-(wins_count[opt] - losses_count[opt]), losses_count[opt], options.index(opt))
    )

    return {
        'matrix': matrix,
        'winners': winners,
        'wins_count': wins_count,
        'losses_count': losses_count,
        'ties_count': ties_count,
        'options': sorted_options
    }

def house_poll_create(request, house_pk):
    house = get_object_or_404(House, pk=house_pk)
    if request.method == 'POST':
        form = HousePollForm(request.POST)
        if form.is_valid():
            poll = form.save(house=house, creator=request.user)
            messages.success(request, f"Poll {poll.question} created.")
            return redirect('polls:house_poll_detail', external_id=poll.external_id)
    else:
        form = HousePollForm()
    return render(request, 'polls/house_poll_form.html', {'form': form, 'house': house})

def house_poll_detail(request, external_id):
    poll = get_object_or_404(HousePoll, external_id=external_id)
    
    # If the poll is finished or user has already voted, redirect to results
    if poll.is_finished or (request.user.is_authenticated and poll.ballots.filter(voter=request.user).exists()):
        return redirect('polls:house_poll_results', external_id=external_id)
        
    return redirect('polls:house_poll_vote', external_id=external_id)

def house_poll_vote(request, external_id):
    poll = get_object_or_404(HousePoll, external_id=external_id)
    if poll.is_finished:
        messages.error(request, "Poll is closed.")
        return redirect('polls:house_poll_results', external_id=external_id)
        
    if request.method == 'POST':
        form = VoteForm(request.POST, poll=poll)
        if form.is_valid():
            try:
                poll.save_ballot(
                    choices=form.get_ranked_choices(),
                    user=request.user,
                    ticket_code=form.cleaned_data.get('ticket_code'),
                    ip_address=get_client_ip(request)
                )
                messages.success(request, "Vote cast successfully!")
                return redirect('polls:house_poll_results', external_id=external_id)
            except ValueError as e:
                messages.error(request, str(e))
    else:
        poll.log_action('VISIT', user=request.user, ip_address=get_client_ip(request))
        form = VoteForm(poll=poll)
    
    is_creator = False
    if poll.creator == request.user:
        is_creator = True

    return render(request, 'polls/poll_vote.html', {'form': form, 'poll': poll, 'is_creator': is_creator})

def house_poll_results(request, external_id):
    poll = get_object_or_404(HousePoll, external_id=external_id)
    poll.log_action('VISIT', user=request.user, ip_address=get_client_ip(request))
    if not poll.is_finished:
         messages.info(request, "Poll is still in progress. Check back later.")
         condorcet_stats = None
    else:
         condorcet_stats = calculate_condorcet(poll)
    
    # Apply governance logic if finished and approved
    if poll.is_finished:
        if poll.poll_type == HousePoll.POLL_TYPE_INTEGRATION:
            if 'Approve' in condorcet_stats['winners'] and len(condorcet_stats['winners']) == 1:
                import re
                from django.contrib.auth import get_user_model
                User = get_user_model()
            
                # Extract the username from the standardized question string
                match = re.search(r"Should we integrate (.+) into", poll.question)
                if match:
                    username = match.group(1)
                    try:
                        user = User.objects.get(username=username)
                        user.houses.add(poll.house)
                    except User.DoesNotExist:
                        pass
                    
        elif poll.poll_type == HousePoll.POLL_TYPE_BANISHMENT:
            if 'Approve' in condorcet_stats['winners'] and len(condorcet_stats['winners']) == 1:
                import re
                from django.contrib.auth import get_user_model
                User = get_user_model()
            
                # Extract the username from the standardized question string
                match = re.search(r"Should we banish (.+) from", poll.question)
                if match:
                    username = match.group(1)
                    try:
                        user = User.objects.get(username=username)
                        user.houses.remove(poll.house)
                    except User.DoesNotExist:
                        pass
                    
        elif poll.poll_type == HousePoll.POLL_TYPE_DELETION:
            if 'Approve' in condorcet_stats['winners'] and len(condorcet_stats['winners']) == 1:
                # Delete the house (which will cascade and delete its polls)
                poll.house.delete()
                messages.warning(request, "The house has been deleted following the successful deletion poll.")
                return redirect('houses:house_list')
                 
    is_creator = False
    if poll.creator == request.user:
        is_creator = True

    return render(request, 'polls/poll_results.html', {
        'poll': poll, 
        'condorcet_stats': condorcet_stats,
        'is_creator': is_creator
    })

def house_poll_export(request, external_id):
    poll = get_object_or_404(HousePoll, external_id=external_id)
    if not poll.is_finished:
        return HttpResponse("Poll is not finished.", status=403)
    results = poll.get_results_json()
    response = HttpResponse(results, content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="house_poll_{external_id}_results.json"'
    return response

def house_poll_tickets_export(request, external_id):
    poll = get_object_or_404(HousePoll, external_id=external_id)
    
    # Check if user is the creator and poll is still active
    if not (poll.is_ticket_secured and not poll.is_finished and request.user == poll.creator):
        return HttpResponse("Unauthorized or poll finished.", status=403)
        
    tickets = [ticket.code for ticket in poll.tickets.all() if not ticket.is_used]
    response = HttpResponse('\n'.join(tickets), content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="house_poll_{external_id}_tickets.txt"'
    return response

# QuickPolls

def quickpoll_create(request):
    if request.method == 'POST':
        form = QuickPollForm(request.POST)
        if form.is_valid():
            poll = form.save(commit=False)
            poll.options = form.cleaned_data['options_text']
            if request.user.is_authenticated:
                poll.owner = request.user
            poll.save()
            messages.success(request, f"QuickPoll created. ID: {poll.external_id}")
            
            # Save the created poll's ID in the session
            created_polls = request.session.get('created_quickpolls', [])
            created_polls.append(str(poll.external_id))
            request.session['created_quickpolls'] = created_polls
            
            return redirect('polls:quickpoll_detail', external_id=poll.external_id)
    else:
        form = QuickPollForm()
    return render(request, 'polls/quickpoll_form.html', {'form': form})

def quickpoll_detail(request, external_id):
    poll = get_object_or_404(QuickPoll, external_id=external_id)
    
    # If the poll is finished or user has already voted, redirect to results
    voted_polls = request.session.get('voted_quickpolls', [])
    if poll.is_finished or str(external_id) in voted_polls or (request.user.is_authenticated and poll.ballots.filter(voter=request.user).exists()):
        return redirect('polls:quickpoll_results', external_id=external_id)
    
    return redirect('polls:quickpoll_vote', external_id=external_id)

def quickpoll_vote(request, external_id):
    poll = get_object_or_404(QuickPoll, external_id=external_id)
    if poll.is_finished:
        messages.error(request, "Poll is closed.")
        return redirect('polls:quickpoll_results', external_id=external_id)
        
    # Check session to prevent duplicate voting from the same computer
    voted_polls = request.session.get('voted_quickpolls', [])
    if str(external_id) in voted_polls:
        messages.error(request, "You have already voted in this poll from this device.")
        return redirect('polls:quickpoll_detail', external_id=external_id)

    if request.method == 'POST':
        form = VoteForm(request.POST, poll=poll)
        if form.is_valid():
            try:
                poll.save_ballot(
                    choices=form.get_ranked_choices(),
                    user=request.user if request.user.is_authenticated else None,
                    ticket_code=form.cleaned_data.get('ticket_code'),
                    ip_address=get_client_ip(request)
                )
                
                # Record the vote in the session
                voted_polls.append(str(external_id))
                request.session['voted_quickpolls'] = voted_polls
                
                messages.success(request, "Vote cast successfully!")
                return redirect('polls:quickpoll_results', external_id=external_id)
            except ValueError as e:
                messages.error(request, str(e))
    else:
        poll.log_action('VISIT', user=request.user, ip_address=get_client_ip(request))
        form = VoteForm(poll=poll)
    
    # Check if the user created this poll
    is_creator = False
    if request.user.is_authenticated and poll.owner == request.user:
        is_creator = True
    elif str(external_id) in request.session.get('created_quickpolls', []):
        is_creator = True

    return render(request, 'polls/poll_vote.html', {'form': form, 'poll': poll, 'is_creator': is_creator})

def quickpoll_results(request, external_id):
    poll = get_object_or_404(QuickPoll, external_id=external_id)
    poll.log_action('VISIT', user=request.user, ip_address=get_client_ip(request))
    
    if not poll.is_finished:
        messages.info(request, "Poll is still in progress. Check back later.")
        condorcet_stats = None
    else:
        condorcet_stats = calculate_condorcet(poll)
    
    # Check if the user created this poll
    is_creator = False
    if request.user.is_authenticated and poll.owner == request.user:
        is_creator = True
    elif str(external_id) in request.session.get('created_quickpolls', []):
        is_creator = True

    return render(request, 'polls/poll_results.html', {
        'poll': poll, 
        'condorcet_stats': condorcet_stats,
        'is_creator': is_creator
    })

def quickpoll_export(request, external_id):
    poll = get_object_or_404(QuickPoll, external_id=external_id)
    if not poll.is_finished:
        return HttpResponse("Poll is not finished.", status=403)
    results = poll.get_results_json()
    response = HttpResponse(results, content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="quickpoll_{external_id}_results.json"'
    return response

def quickpoll_tickets_export(request, external_id):
    poll = get_object_or_404(QuickPoll, external_id=external_id)
    
    # Check if user is the creator (via auth or session) and poll is still active
    is_creator = False
    if request.user.is_authenticated and poll.owner == request.user:
        is_creator = True
    elif str(external_id) in request.session.get('created_quickpolls', []):
        is_creator = True

    if not (poll.is_ticket_secured and not poll.is_finished and is_creator):
        return HttpResponse("Unauthorized or poll finished.", status=403)
        
    tickets = [ticket.code for ticket in poll.tickets.all() if not ticket.is_used]
    response = HttpResponse('\n'.join(tickets), content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="quickpoll_{external_id}_tickets.txt"'
    return response

def quickpoll_archive(request):
    # Wait, queryset for is_finished is hard to do directly in filter for properties.
    # Let's just grab all and filter in python for now or use annotation if needed.
    all_polls = QuickPoll.objects.annotate(
        ballot_count=models.Count('ballots')
    ).order_by('-ballot_count_time')[:20]
    finished_polls = [p for p in all_polls if p.is_finished]
    return render(request, 'polls/quickpoll_archive.html', {'polls': finished_polls})

def poll_join(request):
    if request.method == 'POST':
        poll_id = request.POST.get('poll_id', '').strip()
        if poll_id:
            try:
                # Try QuickPoll first
                poll = QuickPoll.objects.get(external_id=poll_id)
                return redirect('polls:quickpoll_detail', external_id=poll.external_id)
            except QuickPoll.DoesNotExist:
                try:
                    # Then try HousePoll
                    poll = HousePoll.objects.get(external_id=poll_id)
                    return redirect('polls:house_poll_detail', external_id=poll.external_id)
                except HousePoll.DoesNotExist:
                    messages.error(request, "Poll not found. Please check the ID.")
            except (ValidationError, ValueError):
                messages.error(request, "Invalid Poll ID.")
    
    # If it's a GET request or the form had errors, return to home
    return redirect('home')
