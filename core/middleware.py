from django.shortcuts import redirect
from .models import UserProfile

class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print(f"Middleware - Path: {request.path}, Method: {request.method}, Auth: {request.user.is_authenticated}")
        if request.user.is_authenticated:
            profile, created = UserProfile.objects.get_or_create(user=request.user, defaults={'must_change_password': True})
            print(f"Middleware - Must change: {profile.must_change_password}")
            if profile.must_change_password and request.path not in ['/change_password/', '/login/', '/logout/', '/']:
                print("Middleware - Redirecting to change_password")
                return redirect('change_password')
        response = self.get_response(request)
        return response