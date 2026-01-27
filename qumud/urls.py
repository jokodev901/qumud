from django.contrib import admin
from django.urls import path, include
from authentication import urls as auth_urls
from world import urls as world_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include(auth_urls)),
    path('', include(world_urls)),
]