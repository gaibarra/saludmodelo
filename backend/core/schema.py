from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension

class MFASessionScheme(OpenApiAuthenticationExtension):
    target_class='core.authentication.MFASessionAuthentication'
    name='mfaCookieAuth'
    def get_security_definition(self,auto_schema):
        return {'type':'apiKey','in':'cookie','name':settings.SESSION_COOKIE_NAME}
