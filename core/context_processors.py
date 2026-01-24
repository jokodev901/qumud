def htmx_base(request):
    """
    If the request is from HTMX, use the partial base.
    If it's a full page load, use the full base.
    """
    if request.headers.get('HX-Request'):
        return {'base_template': 'core/base_partial.html'}
    return {'base_template': 'core/base.html'}