from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import timedelta
from django.views.generic import CreateView, DetailView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from .models import Poll, Choice, PollSecretKey
from .forms import PollForm
from users.models import House
import secrets

class PollCreateView(LoginRequiredMixin, CreateView):
    model = Poll
    form_class = PollForm
    template_name = 'polls/poll_form.html'

    def get_success_url(self):
        # On redirige vers la vue de détail de la maison actuelle
        return reverse_lazy('house-detail', kwargs={'pk': self.house.pk})

    def dispatch(self, request, *args, **kwargs):
        # On récupère la maison liée au scrutin
        self.house = get_object_or_404(House, pk=self.kwargs['house_id'])
        # Vérification : l'utilisateur doit être membre de la maison pour proposer un scrutin
        if request.user not in self.house.users.all():
            raise PermissionDenied("Vous devez être membre de cette maison pour y proposer un scrutin.")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """
        Injecte l'auteur et la maison dans l'instance du modèle avant la validation du formulaire
        pour que la méthode clean() du modèle puisse y accéder.
        """
        kwargs = super().get_form_kwargs()
        # On initialise une instance de Poll avec les données connues
        kwargs['instance'] = Poll(author=self.request.user, house=self.house)
        return kwargs

    def form_valid(self, form):
        # Récupération des propositions dynamiques depuis la requête POST
        choices = self.request.POST.getlist('choices')
        # Nettoyage : retirer les entrées vides
        choices = [c.strip() for c in choices if c.strip()]
        
        if len(choices) < 2:
            form.add_error(None, "Veuillez ajouter au moins deux propositions valides.")
            return self.form_invalid(form)

        # Sauvegarde d'abord le scrutin
        response = super().form_valid(form)
        
        # Crée les instances de Choice liées à ce scrutin
        for choice_text in choices:
            Choice.objects.create(poll=self.object, text=choice_text)
        
        # Génération des clés secrètes (une par membre de la maison)
        num_participants = self.house.users.count()
        for _ in range(num_participants):
            # Génère une clé aléatoire de 14 caractères hexadécimaux
            key = secrets.token_hex(7)
            PollSecretKey.objects.create(poll=self.object, key=key)
        
        return response

class PollDetailView(LoginRequiredMixin, DetailView):
    model = Poll
    template_name = 'polls/poll_detail.html'
    context_object_name = 'poll'

class PollUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Poll
    form_class = PollForm
    template_name = 'polls/poll_form.html'

    def get_success_url(self):
        return reverse_lazy('poll_detail', kwargs={'pk': self.object.pk})

    def test_func(self):
        # Seul l'auteur du scrutin peut le modifier
        poll = self.get_object()
        return self.request.user == poll.author

class PollDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Poll
    template_name = 'polls/poll_confirm_delete.html'

    def get_success_url(self):
        # Retour à la maison après suppression
        return reverse_lazy('house-detail', kwargs={'pk': self.object.house.pk})

    def test_func(self):
        # Seul l'auteur du scrutin peut le supprimer
        poll = self.get_object()
        return self.request.user == poll.author

class PollKeysDownloadView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Poll

    def test_func(self):
        # Seul l'auteur du scrutin peut télécharger les clés
        poll = self.get_object()
        return self.request.user == poll.author

    def get(self, request, *args, **kwargs):
        poll = self.get_object()
        # Récupère toutes les clés associées
        keys = poll.secret_keys.values_list('key', flat=True)
        
        # Prépare le fichier texte
        content = f"Clés secrètes pour le scrutin : {poll.question}\n"
        content += "="*50 + "\n"
        content += "\n".join(keys)
        
        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="cles_scrutin_{poll.id}.txt"'
        return response
