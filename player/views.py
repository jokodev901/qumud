from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from rest_framework.authtoken.models import Token


class UserProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        token = Token.objects.filter(user=self.request.user).first()

        context['api_key'] = token.key if token else None

        return context

    def post(self, request, *args, **kwargs):
        if "generate_token" in request.POST:
            Token.objects.filter(user=request.user).delete()
            Token.objects.create(user=request.user)

        return redirect('profile')
