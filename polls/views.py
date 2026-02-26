from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import timedelta
from django.views.generic import CreateView, DetailView, UpdateView, DeleteView, ListView
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
        choices_order = data.get('choices_order')
        
        # Vérification si le scrutin utilise les tickets
        if poll.use_tickets:
            secret_key = data.get('secret_key')
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
            
        else:
            # Scrutin sans ticket : validation par l'utilisateur connecté
            user = request.user
            
            # Vérifier que l'utilisateur fait bien partie de la maison
            if user not in poll.house.users.all():
                return JsonResponse({'success': False, 'error': "Vous n'êtes pas membre de cette maison."})
                
            # Vérifier que l'utilisateur n'a pas déjà voté
            if Vote.objects.filter(poll=poll, user=user).exists():
                return JsonResponse({'success': False, 'error': "Vous avez déjà voté pour ce scrutin."})
                
            Vote.objects.create(poll=poll, user=user, choices_order=choices_order)

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
            # === Dépouillement avec la méthode de Condorcet ===
            try:
                votes = self.object.votes.all()
                choices = list(self.object.choices.all())
                choice_ids = [str(c.id) for c in choices]
                
                # Matrice des duels : duels[A][B] = nombre de fois où A est préféré à B
                duels = {a: {b: 0 for b in choice_ids if b != a} for a in choice_ids}
                
                for vote in votes:
                    if not vote.choices_order:
                        continue
                        
                    # On convertit les IDs en chaîne de caractères par sécurité
                    order = [str(choice_id) for choice_id in vote.choices_order]
                    
                    # On compare chaque paire de choix dans l'ordre de préférence du votant
                    for i, a in enumerate(order):
                        for b in order[i+1:]:
                            if a in duels and b in duels[a]:
                                duels[a][b] += 1
                                
                condorcet_winners = []
                
                # On détermine s'il y a un gagnant de Condorcet (quelqu'un qui gagne tous ses duels)
                if votes.exists():
                    for a in choice_ids:
                        is_winner = True
                        for b in choice_ids:
                            if a != b:
                                # A gagne contre B si A est strictement préféré à B plus de fois que B est préféré à A
                                if duels[a][b] <= duels[b][a]:
                                    is_winner = False
                                    break
                        if is_winner:
                            winner_choice = next((c for c in choices if str(c.id) == a), None)
                            if winner_choice:
                                condorcet_winners.append(winner_choice)
                
                context['condorcet_winners'] = condorcet_winners
                context['choices'] = choices
                # On formate les duels pour le template : on associe les objets Choice directement
                formatted_duels = {}
                for a in choices:
                    formatted_duels[a] = {}
                    for b in choices:
                        if a == b:
                            formatted_duels[a][b] = {"score": "-", "opponent_score": "-"}
                        else:
                            score = duels[str(a.id)][str(b.id)]
                            opponent_score = duels[str(b.id)][str(a.id)]
                            formatted_duels[a][b] = {"score": score, "opponent_score": opponent_score}
                    context['duels'] = formatted_duels
                    
                # On prépare les votes pour afficher le texte des choix au lieu des IDs
                choices_dict = {str(c.id): c.text for c in choices}
                formatted_votes = []
                for vote in votes:
                    if vote.choices_order:
                        text_order = [choices_dict.get(str(cid), str(cid)) for cid in vote.choices_order]
                        formatted_votes.append({
                            'secret_key': vote.secret_key,
                            'choices_text': text_order
                        })
                context['formatted_votes'] = formatted_votes
                
            except Exception as e:
                context['condorcet_error'] = str(e)
            # =================================================
            
            return render(request, 'polls/poll_stripping.html', context)
        else:
            return render(request, 'polls/poll_voting.html', context)

class PollResultsDownloadView(LoginRequiredMixin, DetailView):
    model = Poll

    def get(self, request, *args, **kwargs):
        poll = self.get_object()
        
        # Dictionnaire pour remplacer les IDs par les textes
        choices_dict = {str(c.id): c.text for c in poll.choices.all()}
        
        # On rassemble les données de votes pour le JSON
        votes_data = []
        for vote in poll.votes.all():
            if vote.choices_order:
                choices_text = [choices_dict.get(str(cid), str(cid)) for cid in vote.choices_order]
            else:
                choices_text = []
                
            votes_data.append({
                'secret_key': vote.secret_key,
                'choices_order': choices_text,
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

class UserPollsListView(LoginRequiredMixin, ListView):
    model = Poll
    template_name = 'polls/user_poll_list.html'
    context_object_name = 'polls'

    def get_queryset(self):
        # On récupère tous les scrutins des maisons dont l'utilisateur fait partie
        return Poll.objects.filter(house__users=self.request.user).distinct().order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        polls = self.get_queryset()
        
        ongoing_polls = []
        finished_polls = []
        
        # On sépare les scrutins en cours et clôturés via la propriété is_finished
        for poll in polls:
            if poll.is_finished:
                finished_polls.append(poll)
            else:
                ongoing_polls.append(poll)
                
        context['ongoing_polls'] = ongoing_polls
        context['finished_polls'] = finished_polls
        return context
