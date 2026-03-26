from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import House
from .forms import HouseForm, IntegrationPollForm, BanishmentPollForm
from polls.models import HousePoll

@login_required
def house_list(request):
    houses = House.objects.all()
    return render(request, 'houses/house_list.html', {'houses': houses})

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
    return render(request, 'houses/house_detail.html', {'house': house})

@login_required
def create_integration_poll(request, pk):
    house = get_object_or_404(House, pk=pk)
    if request.user != house.creator:
         messages.error(request, "Only the creator can start governance polls.")
         return redirect('houses:house_detail', pk=pk)

    if request.method == 'POST':
        form = IntegrationPollForm(request.POST, house=house)
        if form.is_valid():
            target_user = form.cleaned_data['target_user']
            question = f"Should we integrate {target_user.username} into {house.name}?"
            # We add target_user_id as extra info in question or poll?
            # For now, let's keep it simple.
            messages.success(request, f"Integration poll for {target_user.username} created.")
            return redirect('houses:house_detail', pk=pk)
    else:
        form = IntegrationPollForm(house=house)
    return render(request, 'houses/governance_poll_form.html', {'form': form, 'house': house, 'type': 'Integration'})

@login_required
def create_banishment_poll(request, pk):
    house = get_object_or_404(House, pk=pk)
    if request.user != house.creator:
         messages.error(request, "Only the creator can start governance polls.")
         return redirect('houses:house_detail', pk=pk)

    if request.method == 'POST':
        form = BanishmentPollForm(request.POST, house=house)
        if form.is_valid():
            target_user = form.cleaned_data['target_user']
            question = f"Should we banish {target_user.username} from {house.name}?"
            poll = house.create_governance_poll(question, HousePoll.POLL_TYPE_BANISHMENT)
            messages.success(request, f"Banishment poll for {target_user.username} created.")
            return redirect('houses:house_detail', pk=pk)
    else:
        form = BanishmentPollForm(house=house)
    return render(request, 'houses/governance_poll_form.html', {'form': form, 'house': house, 'type': 'Banishment'})

@login_required
def create_deletion_poll(request, pk):
    house = get_object_or_404(House, pk=pk)
    if request.user != house.creator:
         messages.error(request, "Only the creator can start governance polls.")
         return redirect('houses:house_detail', pk=pk)

    question = f"Should we delete the house {house.name}?"
    poll = house.create_governance_poll(question, HousePoll.POLL_TYPE_DELETION)
    messages.success(request, f"Deletion poll created.")
    return redirect('houses:house_detail', pk=pk)
