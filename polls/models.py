import uuid
import random
import string
import json
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.urls import reverse

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

class PollLog(models.Model):
    """
    Logs events related to polls, such as visits and votes.
    """
    ACTION_TYPES = (
        ('VISIT', 'Visit'),
        ('VOTE', 'Vote'),
    )
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    poll = GenericForeignKey('content_type', 'object_id')
    
    action_type = models.CharField(max_length=10, choices=ACTION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f"{self.action_type} on {self.poll} at {self.timestamp}"

# --- Abstract Base Poll ---

class Poll(models.Model):
    # All poll and quickpoll are identified by a random and unic 8 char long ID
    external_id = models.CharField(max_length=8, default=generate_ticket_code, unique=True, editable=False)
    question = models.CharField(max_length=255)
    options = models.JSONField(default=list, help_text="List of choices for the poll.")
    dead_line = models.DateTimeField()
    max_participants = models.PositiveIntegerField()
    is_ticket_secured = models.BooleanField(default=False)
    ballot_count_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    # Generic relation to access tickets/ballots easily
    tickets = GenericRelation(Ticket)
    ballots = GenericRelation(Ballot)
    logs = GenericRelation(PollLog)

    def log_action(self, action_type, user=None, ip_address=None):
        """
        Creates a PollLog entry for this poll.
        """
        PollLog.objects.create(
            poll=self,
            action_type=action_type,
            user=user if user and user.is_authenticated else None,
            ip_address=ip_address
        )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk is None and not self.ballot_count_time:
            self.ballot_count_time = self.dead_line
        super().save(*args, **kwargs)

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

    def save_ballot(self, choices, user=None, ticket_code=None, ip_address=None):
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
        self.ballot_count_time = timezone.now()
        self.save()
        self.log_action('VOTE', user=user, ip_address=ip_address)
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
        
        # Send an email to all members of the house if the poll is newly created
        if is_new:
            recipient_list = [user.email for user in self.house.users.all() if user.email]
            if recipient_list:
                poll_path = reverse('polls:house_poll_detail', kwargs={'external_id': self.external_id})
                # If you have a configured SITE_URL in settings, you can prefix it here. 
                # e.g., link = f"{settings.SITE_URL}{poll_path}"
                link = f"https://fairpoll.org{poll_path}"
                
                subject = f"New Poll in House {self.house.name}: {self.question}"
                message = (
                    f"A new poll has been created in the house '{self.house.name}'.\n\n"
                    f"Question: {self.question}\n"
                    f"Poll ID: {self.external_id}\n\n"
                    f"You can view and vote on the poll here: {link}\n"
                )
                
                from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@fairpoll.com')
                send_mail(subject, message, from_email, recipient_list, fail_silently=True)

class QuickPoll(Poll):
    """
    A standalone poll accessible via ID.
    """
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
