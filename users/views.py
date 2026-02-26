from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from .models import House
from django.utils import timezone
from datetime import timedelta
from django import forms
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.contrib import messages
from polls.models import Poll, Choice
from .models import User

@login_required
def home_view(request):
    """
    Vue pour la page d'accueil de l'utilisateur connecté.
    Le décorateur @login_required assure que seuls les utilisateurs
    connectés peuvent y accéder.
    """
    return render(request, 'users/home.html')

class HouseListView(LoginRequiredMixin, ListView):
    model = House
    template_name = 'users/house_list.html'
    context_object_name = 'houses'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        # On utilise l'ORM pour filtrer efficacement
        context['my_houses'] = House.objects.filter(users=user)
        context['other_houses'] = House.objects.exclude(users=user)
        return context

class HouseDetailView(LoginRequiredMixin, DetailView):
    model = House
    template_name = 'users/house_detail.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # On récupère tous les scrutins liés à cette maison et on filtre ceux qui sont encore actifs
        # en utilisant la propriété is_finished (qui vérifie la date et la participation totale)
        all_polls = self.object.polls.all()
        context['active_polls'] = [poll for poll in all_polls if not poll.is_finished]
        return context


class HouseCreateView(LoginRequiredMixin, CreateView):
    model = House
    template_name = 'users/house_form.html'
    fields = ['name', 'integration_poll_duration', 'users', 'parent_houses']
    success_url = reverse_lazy('house-list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Utiliser des cases à cocher pour une sélection plus facile au lieu d'une liste déroulante multiple
        form.fields['users'].widget = forms.CheckboxSelectMultiple()
        form.fields['users'].queryset = form.fields['users'].queryset.order_by('username')
        if 'parent_houses' in form.fields:
            form.fields['parent_houses'].widget = forms.CheckboxSelectMultiple()
        return form

    def form_valid(self, form):
        # La méthode de base sauvegarde la maison et les relations ManyToMany (les utilisateurs sélectionnés)
        response = super().form_valid(form)
        
        # On s'assure que l'utilisateur connecté est ajouté à la maison, 
        # même s'il ne s'est pas coché lui-même dans la liste
        self.object.users.add(self.request.user)
        
        return response

class HouseUpdateView(LoginRequiredMixin, UpdateView):
    model = House
    template_name = 'users/house_form.html'
    fields = ['name', 'integration_poll_duration', 'users', 'parent_houses']
    success_url = reverse_lazy('house-list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['users'].widget = forms.CheckboxSelectMultiple()
        if 'parent_houses' in form.fields:
            form.fields['parent_houses'].widget = forms.CheckboxSelectMultiple()
        return form

class HouseDeleteView(LoginRequiredMixin, DeleteView):
    model = House
    template_name = 'users/house_confirm_delete.html'
    success_url = reverse_lazy('house-list')

class RequestIntegrationView(LoginRequiredMixin, View):
    """Permet à un utilisateur de demander à intégrer une maison dont il ne fait pas partie."""
    
    def post(self, request, pk):
        house = get_object_or_404(House, pk=pk)
        
        # Vérification si l'utilisateur est déjà membre
        if request.user in house.users.all():
            messages.warning(request, "Vous faites déjà partie de cette maison.")
            return redirect('house-detail', pk=pk)
            
        question = f"Intégration de {request.user.username} : oui / non"

        # Vérification si un scrutin est déjà en cours
        if Poll.objects.filter(house=house, question=question, deadline__gte=timezone.now()).exists():
            messages.warning(request, "Une demande d'intégration est déjà en cours pour votre compte.")
            return redirect('house-detail', pk=pk)

        # Création du scrutin d'intégration
        deadline = timezone.now() + house.integration_poll_duration
        
        poll = Poll.objects.create(
            author=request.user,
            house=house,
            question=question,
            deadline=deadline,
            use_tickets=False
        )
        Choice.objects.create(poll=poll, text="Oui")
        Choice.objects.create(poll=poll, text="Non")
        
        messages.success(request, "Une demande d'intégration a été créée sous la forme d'un scrutin pour les membres.")
        return redirect('house-detail', pk=pk)

class InviteUserView(LoginRequiredMixin, View):
    """Permet à un membre d'une maison d'inviter un autre utilisateur."""
    
    def post(self, request, house_pk, user_pk):
        house = get_object_or_404(House, pk=house_pk)
        target_user = get_object_or_404(User, pk=user_pk)
        
        # Sécurité : seul un membre peut lancer l'invitation
        if request.user not in house.users.all():
            messages.error(request, "Vous devez être membre de la maison pour inviter quelqu'un.")
            return redirect('house-detail', pk=house_pk)
            
        # Vérification si la cible est déjà membre
        if target_user in house.users.all():
            messages.warning(request, f"{target_user.username} fait déjà partie de la maison.")
            return redirect('house-detail', pk=house_pk)

        question = f"Intégration de {target_user.username}"

        # Vérification si un scrutin est déjà en cours
        if Poll.objects.filter(house=house, question=question, deadline__gte=timezone.now()).exists():
            messages.warning(request, f"Un scrutin d'intégration est déjà en cours pour {target_user.username}.")
            return redirect('house-detail', pk=house_pk)

        # Création du scrutin d'intégration
        deadline = timezone.now() + house.integration_poll_duration
        
        poll = Poll.objects.create(
            author=request.user,
            house=house,
            question=question,
            deadline=deadline,
            use_tickets=False
        )
        Choice.objects.create(poll=poll, text="Oui")
        Choice.objects.create(poll=poll, text="Non")
        
        messages.success(request, f"Un scrutin a été créé pour valider l'intégration de {target_user.username}.")
        return redirect('house-detail', pk=house_pk)
