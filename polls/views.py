from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db import models
from .models import HousePoll, QuickPoll, Ticket, Ballot
from .forms import HousePollForm, QuickPollForm, VoteForm
from houses.models import House

def house_poll_create(request, house_pk):
    house = get_object_or_404(House, pk=house_pk)
    if request.method == 'POST':
        form = HousePollForm(request.POST)
        if form.is_valid():
            poll = form.save(house=house, creator=request.user)
            messages.success(request, f"Poll {poll.question} created.")
            return redirect('polls:house_poll_detail', pk=poll.pk)
    else:
        form = HousePollForm()
    return render(request, 'polls/house_poll_form.html', {'form': form, 'house': house})

def house_poll_detail(request, pk):
    poll = get_object_or_404(HousePoll, pk=pk)
    return render(request, 'polls/house_poll_detail.html', {'poll': poll})

def house_poll_vote(request, pk):
    poll = get_object_or_404(HousePoll, pk=pk)
    if poll.is_finished:
        messages.error(request, "Poll is closed.")
        return redirect('polls:house_poll_results', pk=pk)
        
    if request.method == 'POST':
        form = VoteForm(request.POST, poll=poll)
        if form.is_valid():
            try:
                poll.save_ballot(
                    choices=form.get_ranked_choices(),
                    user=request.user,
                    ticket_code=form.cleaned_data.get('ticket_code')
                )
                messages.success(request, "Vote cast successfully!")
                return redirect('polls:house_poll_detail', pk=pk)
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = VoteForm(poll=poll)
    return render(request, 'polls/poll_vote.html', {'form': form, 'poll': poll})

def house_poll_results(request, pk):
    poll = get_object_or_404(HousePoll, pk=pk)
    if not poll.is_finished:
         messages.info(request, "Poll is still in progress. Check back later.")
    
    stats = {}
    for ballot in poll.ballots.all():
        # Find choices with the best (minimum) rank in this ballot
        if isinstance(ballot.choices, dict):
             best_rank = min(ballot.choices.values()) if ballot.choices else None
             if best_rank is not None:
                 for choice, rank in ballot.choices.items():
                     if rank == best_rank:
                         stats[choice] = stats.get(choice, 0) + 1
                         
    return render(request, 'polls/poll_results.html', {'poll': poll, 'stats': stats})

def house_poll_export(request, pk):
    poll = get_object_or_404(HousePoll, pk=pk)
    if not poll.is_finished:
        return HttpResponse("Poll is not finished.", status=403)
    results = poll.get_results_json()
    response = HttpResponse(results, content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="house_poll_{pk}_results.json"'
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
            return redirect('polls:quickpoll_detail', external_id=poll.external_id)
    else:
        form = QuickPollForm()
    return render(request, 'polls/quickpoll_form.html', {'form': form})

def quickpoll_detail(request, external_id):
    poll = get_object_or_404(QuickPoll, external_id=external_id)
    return render(request, 'polls/quickpoll_detail.html', {'poll': poll})

def quickpoll_vote(request, external_id):
    poll = get_object_or_404(QuickPoll, external_id=external_id)
    if poll.is_finished:
        messages.error(request, "Poll is closed.")
        return redirect('polls:quickpoll_results', external_id=external_id)
        
    if request.method == 'POST':
        form = VoteForm(request.POST, poll=poll)
        if form.is_valid():
            try:
                poll.save_ballot(
                    choices=form.get_ranked_choices(),
                    user=request.user if request.user.is_authenticated else None,
                    ticket_code=form.cleaned_data.get('ticket_code')
                )
                messages.success(request, "Vote cast successfully!")
                return redirect('polls:quickpoll_detail', external_id=external_id)
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = VoteForm(poll=poll)
    return render(request, 'polls/poll_vote.html', {'form': form, 'poll': poll})

def quickpoll_results(request, external_id):
    poll = get_object_or_404(QuickPoll, external_id=external_id)
    stats = {}
    for ballot in poll.ballots.all():
        if isinstance(ballot.choices, dict):
            best_rank = min(ballot.choices.values()) if ballot.choices else None
            if best_rank is not None:
                for choice, rank in ballot.choices.items():
                    if rank == best_rank:
                        stats[choice] = stats.get(choice, 0) + 1
    return render(request, 'polls/poll_results.html', {'poll': poll, 'stats': stats})

def quickpoll_export(request, external_id):
    poll = get_object_or_404(QuickPoll, external_id=external_id)
    if not poll.is_finished:
        return HttpResponse("Poll is not finished.", status=403)
    results = poll.get_results_json()
    response = HttpResponse(results, content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="quickpoll_{external_id}_results.json"'
    return response

def quickpoll_archive(request):
    # Wait, queryset for is_finished is hard to do directly in filter for properties.
    # Let's just grab all and filter in python for now or use annotation if needed.
    all_polls = QuickPoll.objects.all().order_by('-dead_line')
    finished_polls = [p for p in all_polls if p.is_finished]
    return render(request, 'polls/quickpoll_archive.html', {'polls': finished_polls})

def quickpoll_join(request):
    if request.method == 'POST':
        poll_id = request.POST.get('poll_id', '').strip()
        if poll_id:
            try:
                poll = QuickPoll.objects.get(external_id=poll_id)
                return redirect('polls:quickpoll_detail', external_id=poll.external_id)
            except (QuickPoll.DoesNotExist, ValidationError, ValueError):
                messages.error(request, "Poll not found. Please check the ID.")
    
    # If it's a GET request or the form had errors, return to home
    return redirect('home')
