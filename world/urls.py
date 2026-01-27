from django.urls import path
from .views import UserProfileView, GetPlayerCharacters, CreatePlayer, CreateCharacter, SelectCharacter, SelectWorld


urlpatterns = [
    path('', GetPlayerCharacters.as_view(), name='home'),
    path('player', CreatePlayer.as_view(), name='player'),
    path('world', SelectWorld.as_view(), name='world'),
    path('profile', UserProfileView.as_view(), name='profile'),
    path('create_character', CreateCharacter.as_view(), name='create_character'),
    path('select_character', SelectCharacter.as_view(), name='select_character'),
]