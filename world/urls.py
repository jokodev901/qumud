from django.urls import path
from .views import (UserProfileView, GetPlayerCharacters, CreateCharacter, SelectCharacter, SelectWorld,
                    Map, Travel, RegionChat)


urlpatterns = [
    path('', GetPlayerCharacters.as_view(), name='home'),
    path('world', SelectWorld.as_view(), name='world'),
    path('map', Map.as_view(), name='map'),
    path('profile', UserProfileView.as_view(), name='profile'),
    path('create_character', CreateCharacter.as_view(), name='create_character'),
    path('select_character', SelectCharacter.as_view(), name='select_character'),
    path('travel', Travel.as_view(), name='travel'),
    path('region_chat', RegionChat.as_view(), name='region_chat'),
]