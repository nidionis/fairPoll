from django import forms
from django.contrib.auth import get_user_model

from .models import House

User = get_user_model()


class HouseCreateForm(forms.ModelForm):
    members = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": "10"}),
        help_text="Select users to add to this house.",
    )

    class Meta:
        model = House
        fields = ["name"]

    def __init__(self, *args, request_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["members"].queryset = User.objects.filter(is_active=True).order_by("username")
        self.request_user = request_user

    def save(self, commit=True):
        house = super().save(commit=False)
        if self.request_user is not None:
            house.creator = self.request_user
        if commit:
            house.save()
            self.save_m2m()
        return house