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
        exempt_prefixes = ['/admin/', '/__debug__/']  # Added debug toolbar just in case
        exempt_urls = [setup_url, reverse('logout')]
        is_exempt = (
                request.path in exempt_urls or
                any(request.path.startswith(prefix) for prefix in exempt_prefixes)
        )

        has_player = hasattr(request.user, 'player')

        if not has_player and not is_exempt:
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
