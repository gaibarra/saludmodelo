from cryptography.fernet import Fernet
from django.conf import settings
from django.core.checks import Error,register,Tags

@register(Tags.security,deploy=True)
def mfa_configuration(app_configs,**kwargs):
    errors=[]
    if not settings.MFA_REQUIRE_PRIVILEGED:
        errors.append(Error('MFA debe exigirse a perfiles privilegiados antes de desplegar.',id='core.E001'))
    try:Fernet(settings.MFA_ENCRYPTION_KEY.encode())
    except (ValueError,TypeError):
        errors.append(Error('Configure una clave Fernet MFA independiente y custodiada.',id='core.E002'))
    return errors
