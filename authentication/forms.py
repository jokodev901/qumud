from django.contrib.auth.forms import UserCreationForm
from .models import User


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'alias')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['alias'].initial = ""