from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import timedelta
from django.views.generic import CreateView, DetailView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from .models import Poll, Choice, PollSecretKey, Vote
from .forms import PollForm
from users.models import House
import secrets
import json

class PollCreateView(LoginRequiredMixin, CreateView):
    model = Poll
    form_class = PollForm
    template_name = 'polls/poll_form.html'

    def get_success_url(self):
        return reverse_lazy('house-detail', kwargs={'pk': self.house.pk})

    def dispatch(self, request, *args, **kwargs):
        self.house = get_object_or_404(House, pk=self.kwargs['house_id'])
        if request.user not in self.house.users.all():
            raise PermissionDenied("Vous devez être membre de cette maison pour y proposer un scrutin.")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = Poll(author=self.request.user, house=self.house)
        return kwargs

    def form_valid(self, form):
        choices = self.request.POST.getlist('choices')
        choices = [c.strip() for c in choices if c.strip()]
        
        if len(choices) < 2:
            form.add_error(None, "Veuillez ajouter au moins deux propositions valides.")
            return self.form_invalid(form)

        response = super().form_valid(form)
        
        for choice_text in choices:
            Choice.objects.create(poll=self.object, text=choice_text)
        
        num_participants = self.house.users.count()
        for _ in range(num_participants):
            key = secrets.token_hex(7)
            PollSecretKey.objects.create(poll=self.object, key=key)
        
        return response

class PollUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Poll
    form_class = PollForm
    template_name = 'polls/poll_form.html'

    def get_success_url(self):
        return reverse_lazy('poll_detail', kwargs={'pk': self.object.pk})

    def test_func(self):
        poll = self.get_object()
        return self.request.user == poll.author

class PollDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Poll
    template_name = 'polls/poll_confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('house-detail', kwargs={'pk': self.object.house.pk})

    def test_func(self):
        poll = self.get_object()
        return self.request.user == poll.author

class PollKeysDownloadView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Poll

    def test_func(self):
        poll = self.get_object()
        return self.request.user == poll.author

    def get(self, request, *args, **kwargs):
        poll = self.get_object()
        keys = poll.secret_keys.values_list('key', flat=True)
        
        content = f"Clés secrètes pour le scrutin : {poll.question}\n"
        content += "="*50 + "\n"
        content += "\n".join(keys)
        
        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="cles_scrutin_{poll.id}.txt"'
        return response

def poll_vote(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée.'}, status=405)

    poll = get_object_or_404(Poll, pk=pk)

    try:
        data = json.loads(request.body)
        secret_key = data.get('secret_key')
        choices_order = data.get('choices_order')

        if not secret_key:
            return JsonResponse({'success': False, 'error': 'Clé secrète manquante.'})

        try:
            key_obj = PollSecretKey.objects.get(poll=poll, key=secret_key)
        except PollSecretKey.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Clé secrète invalide pour ce scrutin.'})

        if key_obj.is_used:
            return JsonResponse({'success': False, 'error': 'Cette clé a déjà été utilisée pour voter.'})
        
        key_obj.is_used = True
        key_obj.save()

        Vote.objects.create(poll=poll, secret_key=secret_key, choices_order=choices_order)

        return JsonResponse({'success': True})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Données invalides.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# ===== LA NOUVELLE VUE =====
class PollDetailView(LoginRequiredMixin, DetailView):
    model = Poll
    
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        
        # On utilise la propriété de modèle is_finished que vous avez définie
        is_finished = self.object.is_finished 
        context['is_finished'] = is_finished
        
        if is_finished:
            return render(request, 'polls/poll_stripping.html', context)
        else:
            return render(request, 'polls/poll_voting.html', context)

class PollResultsDownloadView(LoginRequiredMixin, DetailView):
    model = Poll

    def get(self, request, *args, **kwargs):
        poll = self.get_object()
        
        # On rassemble les données de votes pour le JSON
        votes_data = []
        for vote in poll.votes.all():
            votes_data.append({
                'secret_key': vote.secret_key,
                'choices_order': vote.choices_order,
            })
            
        data = {
            'poll_id': poll.id,
            'question': poll.question,
            'votes': votes_data
        }
        
        # On renvoie la réponse au format JSON en téléchargement
        response = HttpResponse(json.dumps(data, indent=4), content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="resultats_scrutin_{poll.id}.json"'
        return response
