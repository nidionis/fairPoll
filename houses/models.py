import datetime
from django.db import models
from django.conf import settings
from django.utils import timezone

class House(models.Model):
    name = models.CharField(max_length=100, unique=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_houses"
    )
    # Duration for governance polls (e.g., 3 days)
    default_deadline = models.DurationField(default=datetime.timedelta(days=3))
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def users(self):
        """Returns the users belonging to this house."""
        return self.members.all()

    def create_governance_poll(self, question, poll_type):
        """
        Helper to create a governance poll (banishment, integration, deletion)
        using the default_deadline.
        """
        # We import here to avoid circular dependencies if polls imports House
        from polls.models import HousePoll
    
        deadline = timezone.now() + self.default_deadline
    
        # Max participants is current member count
        max_participants = self.users.count()
        
        # Default options for governance polls
        if options is None:
            options = ["Approve", "Reject"]

        return HousePoll.objects.create(
            house=self,
            question=question,
            options=options,
            dead_line=deadline,
            max_participants=max_participants,
            is_ticket_secured=False,  # Governance usually strictly by user, not ticket
            poll_type=poll_type,
            creator=self.creator  # Or the system/admin
        )
