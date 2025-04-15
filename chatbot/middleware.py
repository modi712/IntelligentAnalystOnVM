from django.shortcuts import redirect
from django.urls import reverse

class AuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # URLs that don't require authentication
        exempt_urls = ['/login/', '/admin/', '/static/']
        
        # Check if request path is exempt
        for url in exempt_urls:
            if request.path.startswith(url):
                return self.get_response(request)
        
        # Check if user is authenticated
        user = request.session.get('user', {})
        if not user.get('is_authenticated', False):
            return redirect('login')
            
        return self.get_response(request)