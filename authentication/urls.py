from django.urls import path
from django.conf.urls import include
from .views import RegisterUser, AllauthLoginView, AllauthSignupView, AllauthLogoutView, AllauthPasswordResetView


urlpatterns = [
    # path('', include('django.contrib.auth.urls')),
    path('register', AllauthSignupView.as_view(), name='account_signup'),
    path('login', AllauthLoginView.as_view(), name='account_login'),
    path('logout', AllauthLogoutView.as_view(), name='account_logout'),

    # enabling this url will automatically include password reset link on login form
    # path('password_reset', AllauthPasswordResetView.as_view(), name='account_reset_password'),
]