from datetime import timedelta
import random
import string

from django.conf import settings
from django.db import models
from django.utils import timezone


def generate_quickpoll_id(length: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    while True:
        candidate = "".join(random.choices(alphabet, k=length))
        if not QuickPoll.objects.filter(poll_id=candidate).exists():
            return candidate


def default_quickpoll_deadline():
    return timezone.now() + timedelta(minutes=10)


class QuickPoll(models.Model):
    poll_id = models.CharField(
        max_length=6,
        unique=True,
        editable=False,
        default=generate_quickpoll_id,
    )
    title = models.CharField(max_length=255)
    max_participants = models.PositiveIntegerField()
    participants_voted_count = models.PositiveIntegerField(default=0)
    duration_minutes = models.PositiveIntegerField(default=10)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_quickpolls",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    deadline_at = models.DateTimeField(default=default_quickpoll_deadline)

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
        return (
            self.participants_voted_count >= self.max_participants
            or timezone.now() >= self.deadline_at
        )

    def expires_at(self):
        return self.created_at + timedelta(hours=24)

    def __str__(self) -> str:
        return f"{self.title} ({self.poll_id})"


class QuickPollProposition(models.Model):
    quickpoll = models.ForeignKey(
        QuickPoll,
        on_delete=models.CASCADE,
        related_name="propositions",
    )
    text = models.CharField(max_length=255)
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ["position"]
        unique_together = [("quickpoll", "position")]

    def __str__(self) -> str:
        return self.text
