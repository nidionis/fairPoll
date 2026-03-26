import datetime
import random
import string
from django.conf import settings
from django.db import models
from django.utils import timezone


class Poll(models.Model):
    """Abstract base class for all poll types"""
    question = models.TextField()
    dead_line = models.DateTimeField()
    max_participants = models.PositiveIntegerField()
    is_ticket_secured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_%(class)s_polls"
    )

    class Meta:
        abstract = True

    @property
    def is_finished(self):
        """Check if the poll is finished (deadline passed or max participants reached)"""
        now = timezone.now()
        ballot_count = self.ballots.count()
        return now > self.dead_line or ballot_count >= self.max_participants

    def generate_tickets(self):
        """Generate tickets for ticket-secured polls"""
        if not self.is_ticket_secured:
            return []
        
        tickets = []
        for i in range(self.max_participants):
            ticket = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            # Make sure ticket is unique within this poll
            while Ticket.objects.filter(poll=self, code=ticket).exists():
                ticket = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            
            ticket_obj = Ticket.objects.create(poll=self, code=ticket)
            tickets.append(ticket_obj)
        
        return tickets

    def get_results_json(self):
        """Return results as JSON for download (only if poll is finished)"""
        if not self.is_finished:
            return None
        
        results = []
        for ballot in self.ballots.all():
            ballot_data = {
                "ticket": ballot.ticket.code if ballot.ticket else None,
                "choices": ballot.get_choices_ordered()
            }
            results.append(ballot_data)
        
        return results


class HousePoll(Poll):
    """Poll associated with a house"""
    house = models.ForeignKey(
        "houses.House",
        on_delete=models.CASCADE,
        related_name="polls"
    )
    options = models.JSONField(default=list)  # List of poll options
    
    POLL_TYPES = [
        ("governance", "Governance Poll"),
        ("custom", "Custom Poll"),
        ("banishment", "Banishment"),
        ("integration", "Integration"),
        ("deletion", "Deletion"),
    ]
    poll_type = models.CharField(max_length=20, choices=POLL_TYPES, default="custom")

    def __str__(self):
        return f"{self.house.name}: {self.question[:50]}..."


class QuickPoll(Poll):
    """Quick poll not tied to any house"""
    options = models.JSONField(default=list)  # List of poll options
    poll_id = models.CharField(max_length=20, unique=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.poll_id:
            self.poll_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            # Ensure uniqueness
            while QuickPoll.objects.filter(poll_id=self.poll_id).exists():
                self.poll_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Quick Poll {self.poll_id}: {self.question[:50]}..."


class Ticket(models.Model):
    """Ticket for secure voting"""
    poll = models.ForeignKey('HousePoll', on_delete=models.CASCADE, related_name='tickets')
    code = models.CharField(max_length=8)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['poll', 'code']

    def __str__(self):
        return f"Ticket {self.code} for {self.poll}"


class Ballot(models.Model):
    """Abstract base class for ballots"""
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        abstract = True

    def get_choices_ordered(self):
        """Return the choices in order for Condorcet method"""
        choices = []
        for choice in self.choices.all().order_by('rank'):
            choices.append(choice.option_index)
        return choices


class HouseBallot(Ballot):
    """Ballot for house polls"""
    poll = models.ForeignKey(HousePoll, on_delete=models.CASCADE, related_name='ballots')
    voter = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    ticket = models.ForeignKey(
        Ticket, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )

    class Meta:
        # Each user can vote only once per poll, or each ticket can be used only once
        constraints = [
            models.UniqueConstraint(
                fields=['poll', 'voter'],
                condition=models.Q(voter__isnull=False),
                name='unique_voter_per_house_poll'
            ),
            models.UniqueConstraint(
                fields=['poll', 'ticket'],
                condition=models.Q(ticket__isnull=False),
                name='unique_ticket_per_house_poll'
            )
        ]

    def __str__(self):
        if self.ticket:
            return f"Ballot (Ticket {self.ticket.code}) for {self.poll}"
        return f"Ballot by {self.voter} for {self.poll}"


class QuickBallot(Ballot):
    """Ballot for quick polls"""
    poll = models.ForeignKey(QuickPoll, on_delete=models.CASCADE, related_name='ballots')
    voter = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    ticket = models.ForeignKey(
        Ticket, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='quick_ballots'
    )

    def __str__(self):
        if self.ticket:
            return f"Quick Ballot (Ticket {self.ticket.code}) for {self.poll}"
        return f"Quick Ballot by {self.voter} for {self.poll}"


class BallotChoice(models.Model):
    """Individual choice within a ballot (for Condorcet ranking)"""
    house_ballot = models.ForeignKey(
        HouseBallot, 
        on_delete=models.CASCADE, 
        related_name='choices',
        null=True,
        blank=True
    )
    quick_ballot = models.ForeignKey(
        QuickBallot, 
        on_delete=models.CASCADE, 
        related_name='choices',
        null=True,
        blank=True
    )
    option_index = models.PositiveIntegerField()  # Index in the poll's options list
    rank = models.PositiveIntegerField()  # 1 = most preferred, 2 = second, etc.

    class Meta:
        # Each option can only appear once per ballot
        constraints = [
            models.UniqueConstraint(
                fields=['house_ballot', 'option_index'],
                condition=models.Q(house_ballot__isnull=False),
                name='unique_option_per_house_ballot'
            ),
            models.UniqueConstraint(
                fields=['quick_ballot', 'option_index'],
                condition=models.Q(quick_ballot__isnull=False),
                name='unique_option_per_quick_ballot'
            ),
            models.UniqueConstraint(
                fields=['house_ballot', 'rank'],
                condition=models.Q(house_ballot__isnull=False),
                name='unique_rank_per_house_ballot'
            ),
            models.UniqueConstraint(
                fields=['quick_ballot', 'rank'],
                condition=models.Q(quick_ballot__isnull=False),
                name='unique_rank_per_quick_ballot'
            )
        ]

    def __str__(self):
        ballot = self.house_ballot or self.quick_ballot
        return f"Choice #{self.option_index} (Rank {self.rank}) for {ballot}"
