from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import timedelta
from .models import HousePoll, QuickPoll

class HousePollForm(forms.ModelForm):
    options_text = forms.CharField(
        widget=forms.Textarea,
        help_text=_("Enter choices, one per line."),
        label=_("Choices")
    )

    class Meta:
        model = HousePoll
        fields = ['question', 'dead_line', 'is_ticket_secured']
        widgets = {
            'dead_line': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def clean_options_text(self):
        data = self.cleaned_data['options_text']
        options = [o.strip() for o in data.splitlines() if o.strip()]
        if len(options) < 2:
            raise forms.ValidationError(_("Please provide at least two options."))
        return options

    def clean_dead_line(self):
        dead_line = self.cleaned_data.get('dead_line')
        if dead_line:
            min_deadline = timezone.now() + timedelta(minutes=1)
            if dead_line < min_deadline:
                raise forms.ValidationError(_("The deadline must be at least 1 minute from now."))
        return dead_line

    def save(self, commit=True, house=None, creator=None):
        instance = super().save(commit=False)
        if house:
            instance.house = house
            instance.max_participants = house.users.count()
        if creator:
            instance.creator = creator
        instance.options = self.cleaned_data['options_text']
        if commit:
            instance.save()
        return instance

class QuickPollForm(forms.ModelForm):
    options_text = forms.CharField(
        widget=forms.Textarea,
        help_text=_("Enter choices, one per line."),
        label=_("Choices")
    )

    class Meta:
        model = QuickPoll
        fields = ['question', 'dead_line', 'max_participants', 'is_ticket_secured']
        widgets = {
            'dead_line': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def clean_options_text(self):
        data = self.cleaned_data['options_text']
        options = [o.strip() for o in data.splitlines() if o.strip()]
        if len(options) < 2:
            raise forms.ValidationError(_("Please provide at least two options."))
        return options

    def clean_dead_line(self):
        dead_line = self.cleaned_data.get('dead_line')
        if dead_line:
            min_deadline = timezone.now() + timedelta(minutes=1)
            if dead_line < min_deadline:
                raise forms.ValidationError(_("The deadline must be at least 1 minute from now."))
        return dead_line

    def clean_max_participants(self):
        max_participants = self.cleaned_data.get('max_participants')
        if max_participants is not None and max_participants < 1:
            raise forms.ValidationError(_("A poll must have at least 1 participant."))
        return max_participants

    def save(self, commit=True, owner=None):
        instance = super().save(commit=False)
        if owner and owner.is_authenticated:
            instance.owner = owner
        instance.options = self.cleaned_data['options_text']
        if commit:
            instance.save()
        return instance

class VoteForm(forms.Form):
    ticket_code = forms.CharField(max_length=8, required=False, label=_("Ticket Code"))

    def __init__(self, *args, **kwargs):
        poll = kwargs.pop('poll')
        super().__init__(*args, **kwargs)
        self.poll = poll

        # In a real Condorcet poll, you'd rank them.
        # For simplicity in this demo, we'll provide a sorted list of choices.
        # But wait, Condorcet needs ranking.
        # Let's use multiple choice fields for simplicity for now, or just comma-separated ranking.
        # Let's say it's comma-separated ranks: "choice1, choice2, choice3"
        for i, option in enumerate(poll.options):
            self.fields[f'rank_{i}'] = forms.IntegerField(
                label=option,
                min_value=1,
                max_value=len(poll.options),
                initial=i+1
            )

    def clean_ticket_code(self):
        code = self.cleaned_data.get('ticket_code')
        if self.poll.is_ticket_secured and not code:
            raise forms.ValidationError(_("This poll is ticket secured. Please enter your ticket code."))
        return code

    def get_ranked_choices(self):
        ranks = {}
        for i, option in enumerate(self.poll.options):
            ranks[option] = self.cleaned_data[f'rank_{i}']
        return ranks
