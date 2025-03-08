from django.shortcuts import redirect
from django.urls import reverse

class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and hasattr(request.user, 'userprofile'):
            if request.user.userprofile.must_change_password and request.path != reverse('change_password'):
                return redirect('change_password')
        return self.get_response(request)