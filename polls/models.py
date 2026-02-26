from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from users.models import User, House
import secrets

def validate_deadline(value):
    if value > timezone.now() + timedelta(days=365):
        raise ValidationError("L'échéance ne peut pas dépasser 1 an.")
    if value <= timezone.now():
        raise ValidationError("L'échéance doit être dans le futur.")

class Poll(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='polls_created')
    house = models.ForeignKey(House, on_delete=models.CASCADE, related_name='polls')
    question = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField(validators=[validate_deadline])
    use_tickets = models.BooleanField(default=True, verbose_name="Sécurisation par ticket")
    voters = models.ManyToManyField(User, related_name='voted_ticketless_polls', blank=True)

    @property
    def is_finished(self):
        # Vérifie si la date d'échéance est passée ou si tout le monde a voté
        total_participants = self.house.users.count()
        votes_count = self.votes.count()
        return timezone.now() > self.deadline or votes_count >= total_participants

    def clean(self):
        # Vérification de la limite de 7 scrutins par jour pour l'auteur
        if not self.pk:
            today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_polls_count = Poll.objects.filter(
                author=self.author,
                created_at__gte=today_start
            ).count()
            if today_polls_count >= 7:
                raise ValidationError("Vous ne pouvez pas proposer plus de 7 scrutins par jour.")

    def __str__(self):
        return f"{self.question} ({self.house.name})"

class Choice(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=255)

    def __str__(self):
        return self.text

class PollSecretKey(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='secret_keys')
    key = models.CharField(max_length=14, unique=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"Clé pour {self.poll.question}"

class Vote(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    # Pour le vote Condorcet, on a besoin de l'ordre des choix au lieu d'un seul choix.
    # On utilise un champ JSON pour stocker cet ordre.
    choices_order = models.JSONField(null=True, blank=True, help_text="Liste ordonnée des ID de Choice")
    secret_key = models.CharField(max_length=14, null=True, blank=True, help_text="Les 14 premiers digits du shasum")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['poll', 'secret_key'], name='unique_vote_with_key', condition=models.Q(secret_key__isnull=False)),
            models.UniqueConstraint(fields=['poll', 'user'], name='unique_vote_without_key', condition=models.Q(user__isnull=False))
        ]

    def __str__(self):
        if self.secret_key:
            return f"Vote sur '{self.poll.question}' par clé {self.secret_key}"
        return f"Vote sur '{self.poll.question}' par {self.user}"