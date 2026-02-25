from django import forms
from django.core.exceptions import ValidationError
from .models import Poll
from django.utils import timezone
from datetime import timedelta
from .models import Poll

class PollForm(forms.ModelForm):
    DURATION_CHOICES = [
        ('minutes', 'Minutes'),
        ('hours', 'Heures'),
        ('days', 'Jours')
    ]

    duration_value = forms.IntegerField(
        min_value=1, 
        initial=1, 
        label="Durée du scrutin",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'style': 'width: 100px; display: inline-block;'})
    )
    
    duration_unit = forms.ChoiceField(
        choices=DURATION_CHOICES,
        initial='days',
        label="",
        widget=forms.Select(attrs={'class': 'form-control', 'style': 'width: 150px; display: inline-block; margin-left: 10px;'})
    )

    class Meta:
        model = Poll
        fields = ['question']  # On retire 'deadline' d'ici
        widgets = {
            'question': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Posez votre question...'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        duration_value = cleaned_data.get('duration_value')
        duration_unit = cleaned_data.get('duration_unit')

        # Calcul automatique de l'échéance (deadline)
        if duration_value and duration_unit:
            # On construit le dictionnaire pour timedelta, par exemple {'days': 2}
            kwargs = {duration_unit: duration_value}
            # On assigne la valeur calculée directement à l'instance
            self.instance.deadline = timezone.now() + timedelta(**kwargs)

        return cleaned_data

    def clean_question(self):
        question = self.cleaned_data.get('question')
        # Vérification si un scrutin avec la même question existe déjà dans cette maison
        if self.instance and self.instance.house_id:
            if Poll.objects.filter(house=self.instance.house, question__iexact=question).exclude(pk=self.instance.pk).exists():
                raise ValidationError("Un scrutin avec cette question existe déjà dans cette maison.")
        return question