from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied

class MFASessionAuthentication(SessionAuthentication):
    def authenticate(self, request):
        from .mfa import status
        result=super().authenticate(request)
        if result and not status(request._request)['authenticated']:
            raise PermissionDenied('Complete la verificación MFA en la página de acceso.',code='mfa_required')
        return result

