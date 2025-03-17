

class DisableCSRFForAPIMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/api/'):  # Adjust this path as necessary
            setattr(request, '_dont_enforce_csrf_checks', True)
        response = self.get_response(request)
        return response