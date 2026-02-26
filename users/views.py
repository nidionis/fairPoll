from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from .models import House
from django.utils import timezone
from datetime import timedelta
from django import forms

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
        # On récupère les scrutins liés à cette maison dont la date d'échéance n'est pas passée
        context['active_polls'] = self.object.polls.filter(deadline__gte=timezone.now())
        return context


class HouseCreateView(LoginRequiredMixin, CreateView):
    model = House
    template_name = 'users/house_form.html'
    fields = ['name', 'users', 'parent_houses']  # On rajoute 'users' ici
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
    fields = ['name', 'users', 'parent_houses']
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
