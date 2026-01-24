from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponse


class PlayerSetupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        setup_url = reverse('player')
        exempt_urls = [setup_url, reverse('logout'), '/admin/']

        has_player = hasattr(request.user, 'player')

        if not has_player and request.path not in exempt_urls:
            return self._handle_redirect(request, setup_url)

        if has_player and request.path == setup_url:
            return self._handle_redirect(request, reverse('home'))

        return self.get_response(request)

    def _handle_redirect(self, request, url):
        if request.headers.get('HX-Request'):
            response = HttpResponse()
            response['HX-Redirect'] = url
            return response
        return redirect(url)
