from django.urls import path
from .views import UserProfileView, GetPlayerCharacters, CreatePlayer, CreateCharacter


urlpatterns = [
    path('', GetPlayerCharacters.as_view(), name='home'),
    path('player', CreatePlayer.as_view(), name='player'),
    path('profile', UserProfileView.as_view(), name='profile'),
    path('create_character', CreateCharacter.as_view(), name='create_character'),
]