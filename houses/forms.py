from django import forms
from django.contrib.auth import get_user_model
from .models import House

User = get_user_model()

class HouseForm(forms.ModelForm):
    members = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select users to add to this house."
    )

    class Meta:
        model = House
        fields = ['name', 'default_deadline']

    def save(self, commit=True, creator=None):
        instance = super().save(commit=False)
        if creator:
            instance.creator = creator
        if commit:
            instance.save()
            # Add creator to house
            if creator:
                creator.houses.add(instance)
            # Add selected members
            for user in self.cleaned_data['members']:
                user.houses.add(instance)
        return instance

class IntegrationPollForm(forms.Form):
    def __init__(self, *args, **kwargs):
        house = kwargs.pop('house')
        super().__init__(*args, **kwargs)
        self.fields['target_user'] = forms.ModelChoiceField(
            queryset=User.objects.exclude(houses=house),
            label="User to integrate"
        )

class BanishmentPollForm(forms.Form):
    def __init__(self, *args, **kwargs):
        house = kwargs.pop('house')
        super().__init__(*args, **kwargs)
        self.fields['target_user'] = forms.ModelChoiceField(
            queryset=house.members.all(),
            label="Member to banish"
        )
