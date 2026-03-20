from django.urls import path
from .views import (UserProfileView, GetPlayerCharacters, CreateCharacter, SelectCharacter, SelectWorld,
                    Map, Travel, RegionChat, Stats, Items)


urlpatterns = [
    path('characters', GetPlayerCharacters.as_view(), name='characters'),
    path('world', SelectWorld.as_view(), name='world'),
    path('items', Items.as_view(), name='items'),
    path('', Map.as_view(), name='home'),
    path('profile', UserProfileView.as_view(), name='profile'),
    path('create_character', CreateCharacter.as_view(), name='create_character'),
    path('select_character', SelectCharacter.as_view(), name='select_character'),
    path('stats', Stats.as_view(), name='stats'),
    path('travel', Travel.as_view(), name='travel'),
    path('region_chat', RegionChat.as_view(), name='region_chat'),
]