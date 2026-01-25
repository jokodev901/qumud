from django import forms
from .models import Player


class PlayerCreationForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ['alias']
        labels = {
            'alias': ''
        }
        widgets = {
            'alias': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter alias...'}),
        }
        error_messages = {
            'alias': {
                'unique': "A player with this in game alias already exists.",
            }
        }