from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import House
from .forms import HouseForm, IntegrationPollForm, BanishmentPollForm
from polls.models import HousePoll

@login_required
def house_list(request):
    my_houses = request.user.houses.all()
    other_houses = House.objects.exclude(id__in=my_houses.values_list('id', flat=True))
    return render(request, 'houses/house_list.html', {
        'my_houses': my_houses,
        'other_houses': other_houses
    })

@login_required
def house_create(request):
    if request.method == 'POST':
        form = HouseForm(request.POST)
        if form.is_valid():
            house = form.save(creator=request.user)
            messages.success(request, f"House {house.name} created successfully.")
            return redirect('houses:house_detail', pk=house.pk)
    else:
        form = HouseForm()
    return render(request, 'houses/house_create.html', {'form': form})

@login_required
def house_detail(request, pk):
    house = get_object_or_404(House, pk=pk)
    all_polls = house.polls.all().order_by('-ballot_count_time')[:100]
    
    active_polls = [p for p in all_polls if not p.is_finished]
    archived_polls = [p for p in all_polls if p.is_finished]

    return render(request, 'houses/house_detail.html', {
        'house': house,
        'members': house.users,
        'active_polls': active_polls,
        'archived_polls': archived_polls
    })

@login_required
def create_integration_poll(request, pk):
    house = get_object_or_404(House, pk=pk)
    if request.user not in house.users:
         messages.error(request, "Only members can start governance polls.")
         return redirect('houses:house_detail', pk=pk)
         
    active_integration_polls = [p for p in house.polls.filter(poll_type=HousePoll.POLL_TYPE_INTEGRATION) if not p.is_finished]
    if active_integration_polls:
         messages.error(request, "An active integration poll already exists.")
         return redirect('houses:house_detail', pk=pk)

    if request.method == 'POST':
        form = IntegrationPollForm(request.POST, house=house)
        if form.is_valid():
            target_user = form.cleaned_data['target_user']
            question = f"Should we integrate {target_user.username} into {house.name}?"
            
            poll = house.create_governance_poll(question, HousePoll.POLL_TYPE_INTEGRATION)
            
            messages.success(request, f"Integration poll for {target_user.username} created.")
            return redirect('polls:house_poll_detail', external_id=poll.external_id)
    else:
        form = IntegrationPollForm(house=house)
    return render(request, 'houses/governance_poll_form.html', {'form': form, 'house': house, 'type': 'Integration'})

@login_required
def create_banishment_poll(request, pk):
    house = get_object_or_404(House, pk=pk)
    if request.user not in house.users and request.user != house.creator:
         messages.error(request, "Only members can start governance polls.")
         return redirect('houses:house_detail', pk=pk)

    active_banishment_polls = [p for p in house.polls.filter(poll_type=HousePoll.POLL_TYPE_BANISHMENT) if not p.is_finished]
    if active_banishment_polls:
         messages.error(request, "An active banishment poll already exists.")
         return redirect('houses:house_detail', pk=pk)

    if request.method == 'POST':
        form = BanishmentPollForm(request.POST, house=house)
        if form.is_valid():
            target_user = form.cleaned_data['target_user']
            question = f"Should we banish {target_user.username} from {house.name}?"
            poll = house.create_governance_poll(question, HousePoll.POLL_TYPE_BANISHMENT)
            messages.success(request, f"Banishment poll for {target_user.username} created.")
            return redirect('polls:house_poll_detail', external_id=poll.external_id)
    else:
        form = BanishmentPollForm(house=house)
    return render(request, 'houses/governance_poll_form.html', {'form': form, 'house': house, 'type': 'Banishment'})

@login_required
def create_deletion_poll(request, pk):
    house = get_object_or_404(House, pk=pk)
    if request.user not in house.users and request.user != house.creator:
         messages.error(request, "Only members can start governance polls.")
         return redirect('houses:house_detail', pk=pk)

    active_deletion_polls = [p for p in house.polls.filter(poll_type=HousePoll.POLL_TYPE_DELETION) if not p.is_finished]
    if active_deletion_polls:
         messages.error(request, "An active deletion poll already exists.")
         return redirect('houses:house_detail', pk=pk)

    question = f"Should we delete the house {house.name}?"
    poll = house.create_governance_poll(question, HousePoll.POLL_TYPE_DELETION)
    messages.success(request, f"Deletion poll created.")
    return redirect('polls:house_poll_detail', external_id=poll.external_id)
