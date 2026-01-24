from django import forms
from .models import Player


class PlayerCreationForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ['alias']