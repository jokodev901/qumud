from django.urls import path
from django.conf.urls import include
from .views import RegisterUser, AllauthLoginView, AllauthSignupView, AllauthLogoutView


urlpatterns = [
    # path('', include('django.contrib.auth.urls')),
    path('register', AllauthSignupView.as_view(), name='account_signup'),
    path('login', AllauthLoginView.as_view(), name='account_login'),
    path('logout', AllauthLogoutView.as_view(), name='account_logout'),
]