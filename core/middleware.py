import sys

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


# middleware.py
class CompanyFilterMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print(
            f"Middleware: User={request.user}, Authenticated={request.user.is_authenticated}, Superuser={request.user.is_superuser}")
        if request.user.is_authenticated:
            if request.user.is_superuser:
                request.company = None
                print(f"Middleware: Superuser {request.user.username} detected, company set to None")
                return self.get_response(request)

            profile = getattr(request.user, 'userprofile', None)
        #    print(f"Middleware: Profile={profile}, Company={profile.company if profile else None}")
            if profile and profile.company:
                request.company = profile.company
        #        print(f"Middleware: Company set to {profile.company.name} for {request.user.username}")
                return self.get_response(request)
            elif not (request.path.startswith('/company_select/') or
                      request.path in ['/login/', '/logout/'] or
                      request.path.startswith('/admin/')):
                print(f"Middleware: Redirecting to company_select for {request.user.username}")
                return redirect('company_select')
        else:
            request.company = None
            print("Middleware: User not authenticated, company set to None")

        response = self.get_response(request)
        return response