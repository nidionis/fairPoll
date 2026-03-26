from django import forms
from django.utils import timezone
from .models import QuickPoll, HousePoll


class QuickPollForm(forms.ModelForm):
    deadline_days = forms.IntegerField(
        initial=1,
        min_value=1,
        max_value=30,
        label="Deadline (in days)",
        help_text="How many days the poll should remain open"
    )

    options_text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        label="Options",
        help_text="Enter each option on a new line"
    )

    class Meta:
        model = QuickPoll
        fields = ['question', 'max_participants', 'is_ticket_secured']
        widgets = {
            'question': forms.Textarea(attrs={'rows': 2}),
        }

    def clean_options_text(self):
        options_text = self.cleaned_data['options_text']
        options = [line.strip() for line in options_text.split('\n') if line.strip()]

        if len(options) < 2:
            raise forms.ValidationError("At least 2 options are required")

        return options

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Set deadline
        days = self.cleaned_data['deadline_days']
        instance.dead_line = timezone.now() + timezone.timedelta(days=days)

        # Set options
        instance.options = self.cleaned_data['options_text']

        if commit:
            instance.save()

        return instance


class VoteForm(forms.Form):
    ticket = forms.CharField(
        max_length=8,
        required=False,
        help_text="Enter your ticket code (if required)"
    )

    def __init__(self, *args, **kwargs):
        self.poll = kwargs.pop('poll')
        super().__init__(*args, **kwargs)

        # Show ticket field only for ticket-secured polls
        if not self.poll.is_ticket_secured:
            del self.fields['ticket']

        # Create choice fields for ranking
        self.options = self.poll.options
        for i, option in enumerate(self.options):
            self.fields[f'choice_{i}'] = forms.IntegerField(
                label=option,
                min_value=1,
                max_value=len(self.options),
                help_text=f"Rank this option (1 = most preferred, {len(self.options)} = least preferred)"
            )

    def clean(self):
        cleaned_data = super().clean()

        # Validate ticket if required
        if self.poll.is_ticket_secured:
            ticket = cleaned_data.get('ticket')
            if not ticket:
                raise forms.ValidationError("Ticket is required for this poll")

        # Collect and validate rankings
        choices = []
        rankings = []

        for i, option in enumerate(self.options):
            rank = cleaned_data.get(f'choice_{i}')
            if rank is not None:
                rankings.append(rank)
                choices.append((rank, option))

        # Check that all rankings are unique
        if len(set(rankings)) != len(rankings):
            raise forms.ValidationError("Each option must have a unique ranking")

        # Check that we have rankings from 1 to len(options)
        if set(rankings) != set(range(1, len(self.options) + 1)):
            raise forms.ValidationError(f"Rankings must be from 1 to {len(self.options)}")

        # Sort by rank and store just the options in order
        choices.sort()  # Sort by rank (first element of tuple)
        cleaned_data['choices'] = [option for rank, option in choices]

        return cleaned_data