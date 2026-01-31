from django import forms
from .models import Entity, World


class CharacterCreationForm(forms.ModelForm):
    class Meta:
        model = Entity
        fields = ['name', 'max_health', 'attack_range', 'attack_damage', 'speed', 'initiative', 'max_targets']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter character name...'}),
            'max_health': forms.NumberInput(attrs={'class': 'form-control'}),
            'attack_range': forms.NumberInput(attrs={'class': 'form-control'}),
            'attack_damage': forms.NumberInput(attrs={'class': 'form-control'}),
            'speed': forms.NumberInput(attrs={'class': 'form-control'}),
            'initiative': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_targets': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class WorldCreationForm(forms.ModelForm):
    name = forms.CharField(max_length=64, label='',
                           widget=forms.TextInput(attrs={'class': 'form-control',
                                                         'placeholder': 'Enter a world name...'}))

    class Meta:
        model = World
        fields = ['name']

    def validate_unique(self):
        # We override the unique validation and tell it to ignore 'name' since we're handling via get_or_create()
        exclude = self._get_validation_exclusions()
        exclude.add('name')
        try:
            self.instance.validate_unique(exclude=exclude)
        except Exception:
            pass