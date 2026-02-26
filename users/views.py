from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from .models import House
from django.utils import timezone
from datetime import timedelta

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
    fields = ['name', 'parent_houses']  # On retire 'users' du formulaire
    success_url = reverse_lazy('house-list')

    def form_valid(self, form):
        # On sauvegarde l'instance de la maison sans la commiter tout de suite
        self.object = form.save(commit=False)
        self.object.save() # Sauvegarde en base pour générer l'ID
        
        # On sauvegarde les relations ManyToMany du formulaire (ici parent_houses)
        form.save_m2m()
        
        # Ensuite, on ajoute l'utilisateur connecté explicitement et uniquement à CETTE maison
        self.object.users.add(self.request.user)
        
        # On redirige vers l'URL de succès
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(self.get_success_url())

class HouseUpdateView(LoginRequiredMixin, UpdateView):
    model = House
    template_name = 'users/house_form.html'
    fields = ['name', 'users', 'parent_houses']
    success_url = reverse_lazy('house-list')

class HouseDeleteView(LoginRequiredMixin, DeleteView):
    model = House
    template_name = 'users/house_confirm_delete.html'
    success_url = reverse_lazy('house-list')
