from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView
from django.contrib.staticfiles.storage import staticfiles_storage
from authentication import urls as auth_urls
from world import urls as world_urls

urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('img/favicon.svg'))),
    path('admin/', admin.site.urls),
    path('auth/', include(auth_urls)),
    path('', include(world_urls)),
]