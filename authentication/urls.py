from django.urls import path
from django.conf.urls import include
from .views import RegisterUser


urlpatterns = [
    path('', include('django.contrib.auth.urls')),
    path('register', RegisterUser.as_view(), name='register'),
]
