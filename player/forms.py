from django import forms
from .models import Player
from world.models import Entity


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


class CharacterCreationForm(forms.ModelForm):
    class Meta:
        model = Entity
        fields = ['name', 'max_health', 'attack_range', 'attack_damage', 'speed', 'initiative', 'max_targets']
        widgets = {
            'alias': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter alias...'}),
            'max_health': forms.NumberInput(attrs={'class': 'form-control'}),
            'attack_range': forms.NumberInput(attrs={'class': 'form-control'}),
            'attack_damage': forms.NumberInput(attrs={'class': 'form-control'}),
            'speed': forms.NumberInput(attrs={'class': 'form-control'}),
            'initiative': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_targets': forms.NumberInput(attrs={'class': 'form-control'}),
        }
