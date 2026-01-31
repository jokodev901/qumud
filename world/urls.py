from django.urls import path
from .views import (UserProfileView, GetPlayerCharacters, CreateCharacter, SelectCharacter, SelectWorld,
                    Map)


urlpatterns = [
    path('', GetPlayerCharacters.as_view(), name='home'),
    path('world', SelectWorld.as_view(), name='world'),
    path('map', Map.as_view(), name='map'),
    path('profile', UserProfileView.as_view(), name='profile'),
    path('create_character', CreateCharacter.as_view(), name='create_character'),
    path('select_character', SelectCharacter.as_view(), name='select_character'),
]