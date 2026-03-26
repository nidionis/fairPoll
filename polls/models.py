import uuid
import random
import string
import json
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType

# --- Utilities ---

def generate_ticket_code():
    """Generates an 8-char alphanumeric string."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(8))

# --- Supporting Models ---

class Ticket(models.Model):
    """
    Represents a secure access token for a poll.
    Linked generically so it works for HousePoll or QuickPoll.
    """
    code = models.CharField(max_length=8, default=generate_ticket_code, unique=True)
    is_used = models.BooleanField(default=False)
    
    # Generic relation to Poll
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    poll = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return f"Ticket {self.code} ({'Used' if self.is_used else 'Available'})"

class Ballot(models.Model):
    """
    Stores a single vote.
    Choices are stored as JSON: {'choice_id': rank} or ['choice1', 'choice2']
    depending on your specific Condorcet implementation.
    """
    # Generic relation to Poll
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    poll = GenericForeignKey('content_type', 'object_id')

    # The actual vote data
    choices = models.JSONField(default=dict)
    
    # If ticket secured, we link the ticket. If not, we track the user.
    ticket = models.OneToOneField(Ticket, null=True, blank=True, on_delete=models.SET_NULL)
    voter = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    
    timestamp = models.DateTimeField(auto_now_add=True)

# --- Abstract Base Poll ---

class Poll(models.Model):
    question = models.CharField(max_length=255)
    options = models.JSONField(default=list, help_text="List of choices for the poll.")
    dead_line = models.DateTimeField()
    max_participants = models.PositiveIntegerField()
    is_ticket_secured = models.BooleanField(default=False)
    
    # Generic relation to access tickets/ballots easily
    tickets = GenericRelation(Ticket)
    ballots = GenericRelation(Ballot)

    class Meta:
        abstract = True

    @property
    def is_finished(self):
        """Poll is finished if deadline passed OR max participants reached."""
        now = timezone.now()
        count = self.ballots.count()
        return now > self.dead_line or count >= self.max_participants

    def generate_tickets(self):
        """Generates tickets equal to max_participants."""
        if not self.is_ticket_secured:
            return
            
        # Clear existing unused tickets if re-generating? 
        # For safety, let's just ensure we have enough.
        current_count = self.tickets.count()
        needed = self.max_participants - current_count
        
        for _ in range(needed):
            Ticket.objects.create(poll=self)

    def save_ballot(self, choices, user=None, ticket_code=None):
        """
        Validates and saves a vote.
        Returns the created Ballot or raises ValueError.
        """
        if self.is_finished:
            raise ValueError("Poll is closed.")

        ticket_obj = None

        if self.is_ticket_secured:
            if not ticket_code:
                raise ValueError("Ticket required.")
            try:
                ticket_obj = self.tickets.get(code=ticket_code, is_used=False)
            except Ticket.DoesNotExist:
                raise ValueError("Invalid or used ticket.")
            
            ticket_obj.is_used = True
            ticket_obj.save()
        else:
            # If not secured, user must be logged in and unique only for HousePoll
            if hasattr(self, 'house'):
                if not user or not user.is_authenticated:
                    raise ValueError("User must be logged in.")
                if self.ballots.filter(voter=user).exists():
                    raise ValueError("User already voted.")
            else:
                # For QuickPoll, only check for double voting if they are authenticated
                if user and user.is_authenticated:
                    if self.ballots.filter(voter=user).exists():
                        raise ValueError("User already voted.")

        # Ensure we don't pass an unauthenticated User object to the voter ForeignKey
        real_voter = user if (user and user.is_authenticated and not self.is_ticket_secured) else None

        ballot = Ballot.objects.create(
            poll=self,
            choices=choices,
            ticket=ticket_obj,
            voter=real_voter
        )
        return ballot

    def get_results_json(self):
        """
        Returns JSON format for verification:
        {{ticket/None: choices...}, ...}
        """
        if not self.is_finished:
            return None # Or raise error
            
        results = {}
        for ballot in self.ballots.all():
            if ballot.ticket:
               key = ballot.ticket.code
            else:
                # Use the ballot's primary key to ensure uniqueness while remaining anonymous
               key = f"Anonymous"
            results[key] = ballot.choices
        return json.dumps(results, indent=2)

    # --- Concrete Poll Implementations ---

class HousePoll(Poll):
    """
    A poll attached to a House.
    """
    POLL_TYPE_STANDARD = 'standard'
    POLL_TYPE_INTEGRATION = 'integration'
    POLL_TYPE_BANISHMENT = 'banishment'
    POLL_TYPE_DELETION = 'deletion'
    
    TYPE_CHOICES = [
        (POLL_TYPE_STANDARD, 'Standard Vote'),
        (POLL_TYPE_INTEGRATION, 'Member Integration'),
        (POLL_TYPE_BANISHMENT, 'Member Banishment'),
        (POLL_TYPE_DELETION, 'House Deletion'),
    ]

    house = models.ForeignKey('houses.House', on_delete=models.CASCADE, related_name='polls')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    poll_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=POLL_TYPE_STANDARD)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and self.is_ticket_secured:
            self.generate_tickets()

class QuickPoll(Poll):
    """
    A standalone poll accessible via ID.
    """
    # QuickPolls might identify by a UUID or a short ID
    external_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Optional owner, but not required
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and self.is_ticket_secured:
            self.generate_tickets()
