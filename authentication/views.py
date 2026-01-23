from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.views.generic.edit import CreateView
from django.contrib.auth import login
from django.conf import settings


from .forms import CustomUserCreationForm


class RegisterUser(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'register.html'

    def form_valid(self, form):
        user = form.save()
        login(self.request, user, backend='django.contrib.auth.backends.ModelBackend')

        next_url = self.request.GET.get('next')
        if next_url:
            return redirect(next_url)

        return redirect(settings.LOGIN_REDIRECT_URL)
