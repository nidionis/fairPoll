from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from dal import autocomplete
from .models import House
import datetime

User = get_user_model()

class HouseForm(forms.ModelForm):
    members = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        widget=autocomplete.ModelSelect2Multiple(
            url='houses:user-autocomplete',
            attrs={'data-placeholder': _('Type username or email...')}
        ),
        help_text=_("Select users to add to this house.")
        widget=autocomplete.ModelSelect2Multiple(url='houses:user-autocomplete'),
        help_text="Select users to add to this house."
    )
    
    default_deadline_days = forms.IntegerField(
        initial=3,
        min_value=1,
        label=_("Default Deadline (in days)"),
        help_text=_("Duration for governance polls.")
    )

    class Meta:
        model = House
        fields = ['name']

    def save(self, commit=True, creator=None):
        instance = super().save(commit=False)
        if creator:
            instance.creator = creator
            
        days = self.cleaned_data.get('default_deadline_days', 3)
        instance.default_deadline = datetime.timedelta(days=days)
        
        if commit:
            instance.save()
            # Add creator to house
            if creator:
                creator.houses.add(instance)
            # Add selected members
            for user in self.cleaned_data.get('members', []):
                user.houses.add(instance)
        return instance

class IntegrationPollForm(forms.Form):
    def __init__(self, *args, **kwargs):
        house = kwargs.pop('house')
        super().__init__(*args, **kwargs)
        self.fields['target_user'] = forms.ModelChoiceField(
            queryset=User.objects.exclude(houses=house),
            label=_("User to integrate")
        )

class BanishmentPollForm(forms.Form):
    def __init__(self, *args, **kwargs):
        house = kwargs.pop('house')
        super().__init__(*args, **kwargs)
        self.fields['target_user'] = forms.ModelChoiceField(
            queryset=house.members.all(),
            label=_("Member to banish")
        )
