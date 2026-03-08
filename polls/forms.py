from django import forms

from .models import QuickPoll, Poll


class QuickPollCreateForm(forms.ModelForm):
    propositions_text = forms.CharField(
        label="Propositions",
        widget=forms.Textarea(
            attrs={
                "rows": 6,
                "placeholder": "One proposition per line",
            }
        ),
        help_text="Enter one proposition per line.",
    )

    class Meta:
        model = QuickPoll
        fields = ["title", "max_participants", "duration_minutes", "propositions_text"]

    def clean_max_participants(self):
        value = self.cleaned_data["max_participants"]
        if value < 1:
            raise forms.ValidationError("The number of participants must be at least 1.")
        return value

    def clean_duration_minutes(self):
        value = self.cleaned_data["duration_minutes"]
        if value < 1:
            raise forms.ValidationError("The duration must be at least 1 minute.")
        return value

    def clean_propositions_text(self):
        raw_value = self.cleaned_data["propositions_text"]
        propositions = [line.strip() for line in raw_value.splitlines() if line.strip()]

        if len(propositions) < 2:
            raise forms.ValidationError("Please enter at least 2 propositions.")

        return propositions


class QuickPollJoinForm(forms.Form):
    poll_id = forms.CharField(
        label="Quick poll ID",
        max_length=6,
        min_length=6,
        help_text="Enter the 6-character quick poll ID.",
    )

    def clean_poll_id(self):
        return self.cleaned_data["poll_id"].strip().upper()

class PollCreateForm(forms.ModelForm):
    propositions_text = forms.CharField(
        label="Propositions",
        widget=forms.Textarea(attrs={"rows": 6, "placeholder": "One proposition per line"}),
        help_text="Enter one proposition per line.",
    )
    is_ticket_secured = forms.BooleanField(
        required=False, 
        label="Enable Ticket Securisation",
        help_text="Generates unique voting tickets for each house member."
    )

    class Meta:
        model = Poll
        fields = ["title", "duration_minutes", "is_ticket_secured", "propositions_text"]

    def clean_duration_minutes(self):
        value = self.cleaned_data["duration_minutes"]
        if value < 1:
            raise forms.ValidationError("The duration must be at least 1 minute.")
        return value

    def clean_propositions_text(self):
        raw_value = self.cleaned_data["propositions_text"]
        propositions = [line.strip() for line in raw_value.splitlines() if line.strip()]
        if len(propositions) < 2:
            raise forms.ValidationError("Please enter at least 2 propositions.")
        return propositions