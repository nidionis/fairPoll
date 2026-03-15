from datetime import timedelta
import random
import string

from django.conf import settings
from django.db import models
from django.utils import timezone

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail


def generate_poll_id(length: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    while True:
        candidate = "".join(random.choices(alphabet, k=length))
        # Ensure it's unique across both models
        if not QuickPoll.objects.filter(poll_id=candidate).exists() and \
           not Poll.objects.filter(poll_id=candidate).exists():
            return candidate

generate_quickpoll_id = generate_poll_id

def default_poll_deadline(duration=10):
    return timezone.now() + timedelta(minutes=duration)


# Alias for old migrations to prevent AttributeError
default_quickpoll_deadline = default_poll_deadline


class AbstractPoll(models.Model):
    poll_id = models.CharField(
        max_length=6,
        unique=True,
        editable=False,
        default=generate_poll_id,
    )
    title = models.CharField(max_length=255)
    participants_voted_count = models.PositiveIntegerField(default=0)
    duration_minutes = models.PositiveIntegerField(default=20)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    deadline_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.duration_minutes < 1:
            self.duration_minutes = 1

        if self.deadline_at is None:
            base_time = self.created_at or timezone.now()
            self.deadline_at = base_time + timedelta(minutes=self.duration_minutes)
        elif self._state.adding:
            self.deadline_at = timezone.now() + timedelta(minutes=self.duration_minutes)

        super().save(*args, **kwargs)

    def is_finished(self) -> bool:
        return timezone.now() >= self.deadline_at


class QuickPoll(AbstractPoll):
    max_participants = models.PositiveIntegerField()

    def is_finished(self) -> bool:
        return (
            self.participants_voted_count >= self.max_participants
            or super().is_finished()
        )

    def __str__(self) -> str:
        return f"QuickPoll: {self.title} ({self.poll_id})"


class Poll(AbstractPoll):
    house = models.ForeignKey(
        "houses.House",
        on_delete=models.CASCADE,
        related_name="polls"
    )
    is_ticket_secured = models.BooleanField(default=False)

    def is_finished(self) -> bool:
        return (
            self.participants_voted_count >= self.house.members.count()
            or super().is_finished()
        )

    def __str__(self) -> str:
        return f"Poll: {self.title} ({self.poll_id})"


class Proposition(models.Model):
    text = models.CharField(max_length=255)
    position = models.PositiveIntegerField()
    # Generic relations or separate foreign keys for factorization
    quickpoll = models.ForeignKey(QuickPoll, null=True, blank=True, on_delete=models.CASCADE, related_name="propositions")
    poll = models.ForeignKey(Poll, null=True, blank=True, on_delete=models.CASCADE, related_name="propositions")

    class Meta:
        ordering = ["position"]

    def __str__(self) -> str:
        return self.text


class Vote(models.Model):
    # Depending on the vote type
    quickpoll = models.ForeignKey(QuickPoll, null=True, blank=True, on_delete=models.CASCADE, related_name="votes")
    poll = models.ForeignKey(Poll, null=True, blank=True, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    
    ordered_propositions_ids = models.CharField(max_length=1024)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_ordered_propositions(self):
        return [int(pid) for pid in self.ordered_propositions_ids.split(',')]


class Ticket(models.Model):
    """
    Generated for ticket-secured polls.
    """
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="tickets")
    code = models.CharField(max_length=6, unique=True, editable=False)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return self.code

@receiver(post_save, sender=Poll)
def notify_house_members(sender, instance, created, **kwargs):
    if created:
        house = instance.house
        subject = f'New Poll in {house.name}: {instance.title}'
        message = 'A new poll has been created in your house. Please check it out and vote!'
        from_email = settings.DEFAULT_FROM_EMAIL  # Ensure this is configured in settings.py
        for member in house.members.all():
            if member.email:  # Check if email exists
                send_mail(subject, message, from_email, [member.email], fail_silently=True)
