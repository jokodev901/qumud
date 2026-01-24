from django.urls import path
from .views import UserProfileView, GetPlayerCharacters, CreatePlayer


urlpatterns = [
    path('', GetPlayerCharacters.as_view(), name='home'),
    path('player', CreatePlayer.as_view(), name='player'),
    path('profile', UserProfileView.as_view(), name='profile'),
]