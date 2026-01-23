from django.contrib import admin
from django.urls import path, include
from authentication import urls as auth_urls
from player import urls as player_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include(auth_urls)),
    path('', include(player_urls)),
]