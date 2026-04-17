from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.translation import gettext as _, gettext_lazy as _l
from dal import autocomplete
from .models import House
from .forms import HouseForm, IntegrationPollForm, BanishmentPollForm
from polls.models import HousePoll

class UserAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Only authenticated users should be able to access this view.
        if not self.request.user.is_authenticated:
            return get_user_model().objects.none()

        qs = get_user_model().objects.all()

        if self.q:
            qs = qs.filter(Q(username__icontains=self.q) | Q(email__icontains=self.q))

        return qs

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
            messages.success(request, _("House %(name)s created successfully.") % {'name': house.name})
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
         messages.error(request, _("Only members can start governance polls."))
         return redirect('houses:house_detail', pk=pk)
         
    active_integration_polls = [p for p in house.polls.filter(poll_type=HousePoll.POLL_TYPE_INTEGRATION) if not p.is_finished]
    if active_integration_polls:
         messages.error(request, _("An active integration poll already exists."))
         return redirect('houses:house_detail', pk=pk)

    if request.method == 'POST':
        form = IntegrationPollForm(request.POST, house=house)
        if form.is_valid():
            target_user = form.cleaned_data['target_user']
            question = _("Should we integrate %(username)s into %(house_name)s?") % {'username': target_user.username, 'house_name': house.name}
            
            poll = house.create_governance_poll(question, HousePoll.POLL_TYPE_INTEGRATION)
            
            messages.success(request, _("Integration poll for %(username)s created.") % {'username': target_user.username})
            return redirect('polls:house_poll_detail', external_id=poll.external_id)
    else:
        form = IntegrationPollForm(house=house)
    return render(request, 'houses/governance_poll_form.html', {'form': form, 'house': house, 'type': 'Integration'})

@login_required
def create_banishment_poll(request, pk):
    house = get_object_or_404(House, pk=pk)
    if request.user not in house.users and request.user != house.creator:
         messages.error(request, _("Only members can start governance polls."))
         return redirect('houses:house_detail', pk=pk)

    active_banishment_polls = [p for p in house.polls.filter(poll_type=HousePoll.POLL_TYPE_BANISHMENT) if not p.is_finished]
    if active_banishment_polls:
         messages.error(request, _("An active banishment poll already exists."))
         return redirect('houses:house_detail', pk=pk)

    if request.method == 'POST':
        form = BanishmentPollForm(request.POST, house=house)
        if form.is_valid():
            target_user = form.cleaned_data['target_user']
            question = _("Should we banish %(username)s from %(house_name)s?") % {'username': target_user.username, 'house_name': house.name}
            poll = house.create_governance_poll(question, HousePoll.POLL_TYPE_BANISHMENT)
            messages.success(request, _("Banishment poll for %(username)s created.") % {'username': target_user.username})
            return redirect('polls:house_poll_detail', external_id=poll.external_id)
    else:
        form = BanishmentPollForm(house=house)
    return render(request, 'houses/governance_poll_form.html', {'form': form, 'house': house, 'type': 'Banishment'})

@login_required
def create_deletion_poll(request, pk):
    house = get_object_or_404(House, pk=pk)
    if request.user not in house.users and request.user != house.creator:
         messages.error(request, _("Only members can start governance polls."))
         return redirect('houses:house_detail', pk=pk)

    active_deletion_polls = [p for p in house.polls.filter(poll_type=HousePoll.POLL_TYPE_DELETION) if not p.is_finished]
    if active_deletion_polls:
         messages.error(request, _("An active deletion poll already exists."))
         return redirect('houses:house_detail', pk=pk)

    question = _("Should we delete the house %(name)s?") % {'name': house.name}
    poll = house.create_governance_poll(question, HousePoll.POLL_TYPE_DELETION)
    messages.success(request, _("Deletion poll created."))
    return redirect('polls:house_poll_detail', external_id=poll.external_id)
