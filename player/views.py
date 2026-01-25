import json

from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render, reverse
from django.http import HttpResponse

from rest_framework.authtoken.models import Token

from .forms import PlayerCreationForm


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


class CreatePlayer(LoginRequiredMixin, View):
    template_name = 'player.html'

    def get(self, request):
        form = PlayerCreationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = PlayerCreationForm(request.POST)
        if form.is_valid():
            player = form.save(commit=False)
            user = request.user
            player.user = user
            player.save()

            if request.headers.get('HX-Request'):
                response = HttpResponse(status=204)
                response['HX-Location'] = reverse('home')

                location_data = {
                    "path": reverse('home'),
                    "target": "#main-content",
                    "swap": "innerHTML"
                }

                response = HttpResponse(status=204)
                response['HX-Location'] = json.dumps(location_data)
                return response

            return redirect('home')

        return render(request, self.template_name, {'form': form})


class GetPlayerCharacters(LoginRequiredMixin, TemplateView):
    template_name = 'player_characters.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        filler_chars = ['Character 1', 'Character 2', 'Character 3', 'Character 4', 'Character 5']
        context['characters'] = filler_chars

        return context
