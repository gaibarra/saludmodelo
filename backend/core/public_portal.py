"""Public service catalogue, private patient requests, and staff confirmation."""
import re
import uuid
from datetime import date
from django.conf import settings
from django.contrib.auth import authenticate,get_user_model,login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError,transaction
from django.db.models import Q
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied,ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle,UserRateThrottle
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema,OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .access import scopes
from .admin_serializers import StrictSerializer
from .models import AppointmentRequest,PatientProfile,Service,RoleAssignment,AuditEvent
from .workflow import Conflict
from .institutional_services import published_services,public_item

PUBLIC_SERVICES=(
    ('odontologia','Odontología','Prevención y atención dental'),
    ('fisioterapia','Fisioterapia','Movimiento y rehabilitación'),
    ('nutricion','Nutrición','Orientación y seguimiento'),
    ('psicologia','Psicología','Atención y acompañamiento'),
    ('ciencias-del-deporte','Ciencias del deporte','Evaluación y readaptación'),
    ('atencion-comunitaria','Atención comunitaria','Servicios de la comunidad'),
)
SLUGS={row[0] for row in PUBLIC_SERVICES}
SITES={'indistinta','cholul','casita'}
STAFF_ROLES={'director','coordinator','manager','clinical'}

def available_slugs():
    today=timezone.localdate()
    return set(Service.objects.filter(confirmed=True,public_slug__in=SLUGS,roleassignment__role__in=STAFF_ROLES,roleassignment__starts__lte=today,roleassignment__ends__gte=today,roleassignment__revoked_at__isnull=True,roleassignment__user__is_active=True).values_list('public_slug',flat=True))

def enabled():
    if not settings.PATIENT_PORTAL_ENABLED:raise PermissionDenied('Las cuentas y solicitudes de pacientes aún no están habilitadas.')

def patient_for(user):
    enabled()
    if not user.is_authenticated:raise PermissionDenied('Ingrese con su cuenta de paciente.')
    profile=PatientProfile.objects.select_related('user').filter(user=user,user__is_active=True).first()
    if not profile:raise PermissionDenied('Ingrese con una cuenta de paciente.')
    return profile

def item(row):
    return {'id':str(row.public_id),'service':row.service_slug,'site_preference':row.site_preference,'preferred_day':row.preferred_day,'status':row.status,'confirmed_start':row.confirmed_start,'confirmed_site':row.confirmed_site,'etag':row.etag,'created_at':row.created_at}

class RegisterInput(StrictSerializer):
    name=serializers.CharField(max_length=150)
    email=serializers.EmailField(max_length=254)
    phone=serializers.CharField(max_length=20)
    password=serializers.CharField(min_length=12,max_length=128,trim_whitespace=False,write_only=True)
    def validate_phone(self,value):
        digits=re.sub(r'\D','',value)
        if not 10<=len(digits)<=15:raise serializers.ValidationError('Indique un teléfono de 10 a 15 dígitos.')
        return digits
    def validate_name(self,value):
        if len(value.strip())<2:raise serializers.ValidationError('Indique su nombre.')
        return value.strip()

class LoginInput(StrictSerializer):
    email=serializers.EmailField(max_length=254)
    password=serializers.CharField(trim_whitespace=False,write_only=True)

class PatientAppointmentInput(StrictSerializer):
    service=serializers.ChoiceField(choices=sorted(SLUGS))
    site_preference=serializers.ChoiceField(choices=sorted(SITES))
    preferred_day=serializers.DateField(required=False,allow_null=True)
    client_key=serializers.UUIDField()
    def validate_preferred_day(self,value):
        if value and value<timezone.localdate():raise serializers.ValidationError('La fecha preferida debe ser futura o de hoy.')
        return value

class WithdrawInput(StrictSerializer):
    version=serializers.IntegerField(min_value=1)

class StaffDecisionInput(StrictSerializer):
    version=serializers.IntegerField(min_value=1)
    action=serializers.ChoiceField(choices=['confirm','decline'])
    confirmed_start=serializers.DateTimeField(required=False,allow_null=True)
    confirmed_site=serializers.ChoiceField(choices=sorted(SITES),required=False)
    def validate(self,data):
        if data['action']=='confirm':
            if not data.get('confirmed_start') or data['confirmed_start']<=timezone.now():raise serializers.ValidationError('Indique fecha y hora futuras para confirmar.')
            if data.get('confirmed_site') not in SITES-{'indistinta'}:raise serializers.ValidationError('Indique la sede confirmada.')
        elif data.get('confirmed_start') or data.get('confirmed_site'):
            raise serializers.ValidationError('No indique horario al rechazar disponibilidad.')
        return data

class PublicServices(APIView):
    authentication_classes=[]
    permission_classes=[AllowAny]
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request):
        available=available_slugs() if settings.PATIENT_PORTAL_ENABLED else set()
        return Response({'services':[{'slug':slug,'name':name,'summary':summary,'request_enabled':slug in available} for slug,name,summary in PUBLIC_SERVICES],'appointments_enabled':settings.PATIENT_PORTAL_ENABLED,'published_services':[public_item(row) for row in published_services()]})

class PatientRegister(APIView):
    authentication_classes=[SessionAuthentication]
    permission_classes=[AllowAny]
    throttle_classes=[AnonRateThrottle]
    @extend_schema(request=RegisterInput,responses=OpenApiTypes.OBJECT)
    @method_decorator(csrf_protect)
    def post(self,request):
        enabled()
        data=RegisterInput(data=request.data);data.is_valid(raise_exception=True);v=data.validated_data
        email=v['email'].strip().casefold()
        try:validate_password(v['password'])
        except DjangoValidationError as error:raise ValidationError({'password':error.messages})
        User=get_user_model()
        try:
            with transaction.atomic():
                user=User.objects.create_user(username='paciente_'+uuid.uuid4().hex,email=email,password=v['password'],first_name=v['name'])
                PatientProfile.objects.create(user=user,email_normalized=email,phone=v['phone'])
        except IntegrityError:raise ValidationError({'email':'No se pudo crear esta cuenta. Revise el correo o utilice el acceso existente.'})
        login(request,user)
        return Response({'authenticated':True,'name':user.first_name,'email':email,'csrf':get_token(request)},status=201)

class PatientSession(APIView):
    authentication_classes=[SessionAuthentication]
    permission_classes=[AllowAny]
    throttle_classes=[AnonRateThrottle,UserRateThrottle]
    def finalize_response(self,request,response,*args,**kwargs):
        response=super().finalize_response(request,response,*args,**kwargs);response['Cache-Control']='no-store';return response
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request):
        profile=PatientProfile.objects.filter(user=request.user,user__is_active=True).first() if request.user.is_authenticated and settings.PATIENT_PORTAL_ENABLED else None
        return Response({'enabled':settings.PATIENT_PORTAL_ENABLED,'authenticated':bool(profile),'name':profile.user.first_name if profile else '', 'email':profile.email_normalized if profile else '', 'csrf':get_token(request)})
    @extend_schema(request=LoginInput,responses=OpenApiTypes.OBJECT)
    @method_decorator(csrf_protect)
    def post(self,request):
        enabled()
        data=LoginInput(data=request.data);data.is_valid(raise_exception=True);v=data.validated_data
        profile=PatientProfile.objects.select_related('user').filter(email_normalized=v['email'].strip().casefold(),user__is_active=True).first()
        user=authenticate(request,username=profile.user.username,password=v['password']) if profile else None
        if not user:return Response({'detail':'Correo o contraseña incorrectos.'},status=400)
        login(request,user)
        return Response({'enabled':True,'authenticated':True,'name':user.first_name,'email':profile.email_normalized,'csrf':get_token(request)})

class PatientAppointments(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request):
        profile=patient_for(request.user)
        rows=AppointmentRequest.objects.filter(patient=profile).order_by('-id')[:100]
        response=Response({'results':[item(row) for row in rows]});response['Cache-Control']='private, no-store';return response
    @extend_schema(request=PatientAppointmentInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request):
        profile=patient_for(request.user)
        data=PatientAppointmentInput(data=request.data);data.is_valid(raise_exception=True);v=data.validated_data
        if v['service'] not in available_slugs():raise ValidationError({'service':'Este servicio todavía no recibe solicitudes.'})
        previous=AppointmentRequest.objects.filter(patient=profile,client_key=v['client_key']).first()
        if previous:
            if (previous.service_slug,previous.site_preference,previous.preferred_day)!=(v['service'],v['site_preference'],v.get('preferred_day')):raise ValidationError('Clave usada para otra solicitud.')
            return Response(item(previous),status=200)
        if AppointmentRequest.objects.filter(patient=profile,service_slug=v['service'],status='pending').exists():raise ValidationError('Ya tiene una solicitud pendiente para este servicio.')
        row=AppointmentRequest.objects.create(patient=profile,service_slug=v['service'],site_preference=v['site_preference'],preferred_day=v.get('preferred_day'),client_key=v['client_key'])
        return Response(item(row),status=201)

class PatientAppointmentDetail(APIView):
    @extend_schema(request=WithdrawInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,public_id):
        profile=patient_for(request.user)
        data=WithdrawInput(data=request.data);data.is_valid(raise_exception=True)
        row=get_object_or_404(AppointmentRequest.objects.select_for_update(),public_id=public_id,patient=profile)
        if row.etag!=data.validated_data['version']:raise Conflict()
        if row.status!='pending':raise ValidationError('Sólo se puede retirar una solicitud pendiente.')
        row.status='withdrawn';row.etag+=1;row.save(update_fields=['status','etag'])
        return Response(item(row))

class StaffAppointments(APIView):
    @extend_schema(parameters=[OpenApiParameter('service',OpenApiTypes.STR,description='Servicio público asignado'),OpenApiParameter('before',OpenApiTypes.INT,description='Identificador anterior para paginar')],responses=OpenApiTypes.OBJECT)
    def get(self,request):
        enabled()
        slugs=set(Service.objects.filter(pk__in=scopes(request.user,STAFF_ROLES),confirmed=True,public_slug__in=SLUGS).values_list('public_slug',flat=True))
        selected=request.query_params.get('service')
        if selected and selected not in slugs:raise PermissionDenied('Servicio no asignado.')
        q=AppointmentRequest.objects.filter(service_slug__in=slugs)
        if selected:q=q.filter(service_slug=selected)
        before=request.query_params.get('before')
        if before:
            try:pk=int(before)
            except ValueError:raise ValidationError('Paginación inválida.')
            if pk<1:raise ValidationError('Paginación inválida.')
            q=q.filter(pk__lt=pk)
        rows=list(q.select_related('patient__user').order_by('-id')[:51]);next_before=rows[49].pk if len(rows)>50 else None
        results=[{**item(row),'patient_name':row.patient.user.first_name,'patient_email':row.patient.email_normalized,'patient_phone':row.patient.phone} for row in rows[:50]]
        response=Response({'results':results,'next_before':next_before,'services':sorted(slugs)});response['Cache-Control']='private, no-store';return response

class StaffAppointmentDecision(APIView):
    @extend_schema(request=StaffDecisionInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,public_id):
        enabled()
        row=get_object_or_404(AppointmentRequest.objects.select_for_update().select_related('patient__user'),public_id=public_id)
        service=Service.objects.filter(public_slug=row.service_slug,confirmed=True,pk__in=scopes(request.user,STAFF_ROLES)).first()
        if not service:raise PermissionDenied('No tiene permiso vigente para confirmar esta solicitud.')
        data=StaffDecisionInput(data=request.data);data.is_valid(raise_exception=True);v=data.validated_data
        if row.etag!=v['version']:raise Conflict()
        if row.status!='pending':raise ValidationError('La solicitud ya no está pendiente.')
        row.status='confirmed' if v['action']=='confirm' else 'declined'
        row.confirmed_start=v.get('confirmed_start') if row.status=='confirmed' else None
        row.confirmed_site=v.get('confirmed_site','') if row.status=='confirmed' else ''
        row.reviewed_by=request.user;row.reviewed_at=timezone.now();row.etag+=1
        row.save(update_fields=['status','confirmed_start','confirmed_site','reviewed_by','reviewed_at','etag'])
        AuditEvent.objects.create(actor=request.user,service=service,action='appointment.'+row.status,object_id=str(row.public_id))
        return Response(item(row))
