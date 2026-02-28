from django import forms
from .models import Player, World, PlayerClass


class CharacterCreateForm(forms.Form):
    character_name = forms.CharField(max_length=32, min_length=2)
    character_class = forms.ModelChoiceField(queryset=PlayerClass.objects.all())

    def clean_character_name(self):
        name = self.cleaned_data['character_name']

        if Player.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError("This name is already taken.")

        return name


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