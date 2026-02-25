from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import timedelta
from django.views.generic import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from .models import Poll, Choice
from .forms import PollForm
from users.models import House

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
            
        return response

