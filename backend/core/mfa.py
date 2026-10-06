"""Account-bound MFA. Secrets encrypted separately from the database/session key."""
import hashlib
import hmac
import secrets
from datetime import timedelta
import pyotp
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.contrib.auth import get_user_model
from django.middleware.csrf import get_token
from django.db import transaction
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers
from .admin_serializers import StrictSerializer
from .models import MFADevice, SecurityEvent, InstitutionMandate, RoleAssignment, SchoolMandate

PRIVILEGED={'director','coordinator','manager','compliance','clinical','technical','developer'}


def cipher():
    try:
        return Fernet(settings.MFA_ENCRYPTION_KEY.encode())
    except (ValueError, TypeError):
        raise PermissionDenied('MFA requiere configuración de la clave de cifrado por el operador autorizado.')


def required(user):
    if not settings.MFA_REQUIRE_PRIVILEGED:
        return False
    today=timezone.localdate()
    return bool(user.is_staff or user.is_superuser or
        SchoolMandate.objects.filter(user=user,starts__lte=today,ends__gte=today,revoked_at__isnull=True).exists() or
        InstitutionMandate.objects.filter(user=user,starts__lte=today,ends__gte=today).exists() or
        RoleAssignment.objects.filter(user=user,role__in=PRIVILEGED,starts__lte=today,ends__gte=today,revoked_at__isnull=True).exists())


def verified(request, device):
    stamp=request.session.get('mfa_verified_at',0)
    return bool(device and device.enabled and not device.recovery_required and request.session.get('mfa_generation')==device.generation
                and 0<=timezone.now().timestamp()-stamp<12*3600)


def recovery_bound(request,device):
    nonce=request.session.get('exceptional_recovery_nonce','')
    return bool(device and device.recovery_required and nonce and device.recovery_session_hash and
                hmac.compare_digest(hashlib.sha256(nonce.encode()).hexdigest(),device.recovery_session_hash))


def status(request):
    user=request.user
    demo_password_only=settings.MFA_DEMO_PASSWORD_ONLY and not settings.PATIENT_PORTAL_ENABLED
    pilot_password_only=settings.MFA_PASSWORD_ONLY_PILOT
    if not user.is_authenticated:
        return {'authenticated':False,'username':'','mfa_required':False,'mfa_enabled':False,'mfa_verified':False,'password_only_demo':demo_password_only,'password_only_pilot':pilot_password_only}
    device=MFADevice.objects.filter(user=user).first()
    needed=not (demo_password_only or pilot_password_only) and (required(user) or bool(device and (device.enabled or device.recovery_required)))
    checked=verified(request,device)
    return {'authenticated':not needed or checked,'username':user.username,'mfa_required':needed,
            'mfa_enabled':bool(device and device.enabled),'mfa_verified':checked,'password_only_demo':demo_password_only,'password_only_pilot':pilot_password_only,
            'mfa_configured':bool(settings.MFA_ENCRYPTION_KEY),
            'recovery_pending':bool(device and device.recovery_required),
            'recovery_enrollment_allowed':recovery_bound(request,device),
            'recovery_remaining':len(device.recovery_hashes) if device else 0}




def event(user,action):
    SecurityEvent.objects.create(user=user,action=action)


def stamp(request,device):
    request.session.cycle_key()
    request.session['mfa_generation']=device.generation
    request.session['mfa_verified_at']=timezone.now().timestamp()


def bad(device,user):
    device.failures+=1
    if device.failures>=5:
        device.locked_until=timezone.now()+timedelta(minutes=5)
        device.failures=0
    device.save()
    event(user,'mfa.failed')
    return Response({'detail':'Contraseña o código incorrecto, vencido o ya utilizado.'},status=400)


@sensitive_variables()
def step_for(secret,code,last_step=-1):
    if len(code)!=6 or not code.isascii() or not code.isdigit():return None
    step=int(timezone.now().timestamp())//30
    totp=pyotp.TOTP(secret)
    for candidate in (step+1,step,step-1):
        if candidate>last_step and hmac.compare_digest(totp.at(candidate*30),code):return candidate
    return None


@sensitive_variables()
def proof(device,code):
    normalized=code.strip().replace('-','').lower()
    value=hashlib.sha256(normalized.encode()).hexdigest()
    for existing in device.recovery_hashes:
        if hmac.compare_digest(existing,value):
            device.recovery_hashes=[item for item in device.recovery_hashes if item!=existing]
            device.generation+=1  # Also revoke other authenticated sessions on recovery.
            device.pending_secret='';device.pending_nonce='';device.pending_until=None
            return 'recovery'
    try:
        secret=cipher().decrypt(device.secret.encode()).decode()
    except (InvalidToken,UnicodeDecodeError):
        raise PermissionDenied('No se pudo abrir el autenticador; solicite revisión de la clave de cifrado.')
    step=step_for(secret,code,device.last_step)
    if step is None:return None
    device.last_step=step
    return 'totp'


@sensitive_variables()
def recovery_codes(device):
    raw=[secrets.token_hex(16) for _ in range(8)]
    device.recovery_hashes=[hashlib.sha256(code.encode()).hexdigest() for code in raw]
    return ['-'.join(code[i:i+8] for i in range(0,32,8)) for code in raw]


class MFAInput(StrictSerializer):
    action=serializers.ChoiceField(choices=['begin','confirm','verify','codes','recover'])
    password=serializers.CharField(required=False,allow_blank=True,max_length=1024,trim_whitespace=False,write_only=True)
    code=serializers.CharField(required=False,allow_blank=True,max_length=80,write_only=True)


class MFAView(APIView):
    # Password-authenticated partial sessions may access ONLY session/MFA endpoints.
    authentication_classes=[SessionAuthentication]
    permission_classes=[IsAuthenticated]
    def finalize_response(self,request,response,*args,**kwargs):
        response=super().finalize_response(request,response,*args,**kwargs)
        response['Cache-Control']='no-store'
        return response

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request):
        return Response({**status(request),'csrf':get_token(request)})

    @extend_schema(request=MFAInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    @sensitive_variables()
    def post(self,request):
        form=MFAInput(data=request.data);form.is_valid(raise_exception=True)
        data=form.validated_data
        user=get_user_model().objects.select_for_update().get(pk=request.user.pk)
        device,_=MFADevice.objects.get_or_create(user=user)
        # User lock serializes creation and every attempt, including concurrent recovery.
        now=timezone.now()
        if device.locked_until and device.locked_until>now:
            return Response({'detail':'Demasiados intentos. Espere cinco minutos.'},status=429)
        login_at=request.session.get('password_login_at',0)
        if not verified(request,device) and not 0<=now.timestamp()-login_at<600:
            return Response({'detail':'La sesión de verificación venció; vuelva a ingresar con su contraseña.'},status=403)
        action=data['action'];password=data.get('password','');code=data.get('code','')
        extra={}
        if device.recovery_required and action!='recover':
            if action not in {'begin','confirm'} or not recovery_bound(request,device):
                return Response({'detail':'Complete la recuperación excepcional y configure un nuevo autenticador en la misma sesión.'},status=403)
        if action=='recover':
            from .exceptional_mfa import redeem
            if not redeem(request,user,device,password,code):return bad(device,user)
        elif action in {'begin','codes'}:
            if not user.check_password(password):return bad(device,user)
            if device.enabled:
                used=proof(device,code)
                if not used:return bad(device,user)
                event(user,'mfa.'+used)
                stamp(request,device)
            elif action=='codes':
                return Response({'detail':'Active primero el autenticador.'},status=400)
            if action=='begin':
                secret=pyotp.random_base32()
                nonce=secrets.token_hex(32)
                device.pending_secret=cipher().encrypt(secret.encode()).decode()
                device.pending_nonce=hashlib.sha256(nonce.encode()).hexdigest()
                device.pending_until=now+timedelta(minutes=10)
                request.session['mfa_setup_nonce']=nonce
                extra={'setup_secret':secret,'issuer':'Salud Modelo','account':user.username,'expires_in':600}
                event(user,'mfa.setup_started')
            else:
                extra={'recovery_codes':recovery_codes(device)}
                device.generation+=1
                stamp(request,device)
                event(user,'mfa.codes_regenerated')
        elif action=='confirm':
            nonce=request.session.get('mfa_setup_nonce','')
            if not device.pending_until or device.pending_until<=now or not nonce or not hmac.compare_digest(hashlib.sha256(nonce.encode()).hexdigest(),device.pending_nonce):
                return Response({'detail':'La configuración venció o pertenece a otra sesión. Iníciela nuevamente.'},status=400)
            try:secret=cipher().decrypt(device.pending_secret.encode()).decode()
            except InvalidToken:raise PermissionDenied('Clave de cifrado incompatible con la configuración pendiente.')
            step=step_for(secret,code)
            if step is None:return bad(device,user)
            if device.recovery_required:
                from .exceptional_mfa import complete
                complete(request,user,device)
            device.secret=device.pending_secret;device.enabled=True;device.last_step=step
            device.recovery_required=False;device.recovery_session_hash=''
            request.session.pop('exceptional_recovery_nonce',None)
            device.generation+=1
            device.pending_secret='';device.pending_nonce='';device.pending_until=None
            request.session.pop('mfa_setup_nonce',None)
            extra={'recovery_codes':recovery_codes(device)}
            stamp(request,device)
            event(user,'mfa.enabled')
        else:
            if not device.enabled:return Response({'detail':'Configure primero su autenticador.'},status=400)
            used=proof(device,code)
            if not used:return bad(device,user)
            stamp(request,device)
            event(user,'mfa.'+used)
        device.failures=0;device.locked_until=None;device.save()
        return Response({**status(request),'csrf':get_token(request),**extra})
