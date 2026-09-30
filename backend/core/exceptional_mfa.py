"""Dual-control recovery of an enrolled MFA account; no direct business access."""
import hashlib
import hmac
import secrets
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied,ValidationError
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from .models import ExceptionalMFARecovery,MFADevice,Institution,InstitutionMember,InstitutionMandate,RoleAssignment,GovernanceEvent
from .admin_serializers import StrictSerializer
from .governance import managed_institutions,record
from .mfa import verified,event
from .tracking.views import Private
from .workflow import Conflict


def enabled():
    if not settings.EXCEPTIONAL_MFA_RECOVERY_ENABLED:
        raise PermissionDenied('La recuperación excepcional requiere habilitación y procedimiento institucional aprobado.')


def authority(user,institution,generation=None):
    if not get_user_model().objects.filter(pk=user.pk,is_active=True).exists() or institution not in managed_institutions(user):
        raise PermissionDenied('Requiere mandato institucional vigente.')
    device=MFADevice.objects.filter(user=user,enabled=True,recovery_required=False).first()
    if not device or (generation is not None and device.generation!=generation):
        raise PermissionDenied('La verificación del responsable cambió; requiere una nueva solicitud.')
    return device


def recent(request,institution):
    device=authority(request.user,institution)
    if not verified(request,device) or not 0<=timezone.now().timestamp()-request.session.get('mfa_verified_at',0)<600:
        raise PermissionDenied('Verifique nuevamente su MFA en Seguridad; se requieren menos de diez minutos.')
    return device


def eligible(target,institution):
    # Global login recovery cannot be authorized by a single tenant for a shared account.
    memberships=set(InstitutionMember.objects.filter(user=target).values_list('institution_id',flat=True))
    memberships.update(InstitutionMandate.objects.filter(user=target).values_list('institution_id',flat=True))
    memberships.update(RoleAssignment.objects.filter(user=target).values_list('service__site__campus__institution_id',flat=True))
    technical=RoleAssignment.objects.filter(user=target,role__in={'technical','developer'}).exists()
    if not target.is_active or target.is_staff or target.is_superuser or technical or memberships!={institution}:
        raise PermissionDenied('Cuenta no elegible para este procedimiento institucional. Requiere revisión del operador autorizado.')


def row(value):
    return {key:getattr(value,key) for key in ['id','institution_id','expected_generation','state','rationale','verification_reference','review_reason','review_reference','created_at','reviewed_at','consumed_at','completed_at','expires_at']} | {
        'target':value.target.username,'requested_by':value.requested_by.username,'reviewed_by':value.reviewed_by.username if value.reviewed_by_id else None,'expired':value.expires_at<=timezone.now(),
        'revocation':GovernanceEvent.objects.filter(institution_id=value.institution_id,action='mfa.recovery_revoked',object_id=str(value.pk)).order_by('-id').values('actor__username','created_at','rationale').first()}


class ExceptionalRecoveryInput(StrictSerializer):
    institution=serializers.IntegerField(min_value=1)
    username=serializers.CharField(max_length=150)
    rationale=serializers.CharField(max_length=2000)
    verification_reference=serializers.CharField(max_length=250)
    client_key=serializers.UUIDField()
class ExceptionalRecoveryPageInput(StrictSerializer):
    before=serializers.IntegerField(min_value=1,max_value=9223372036854775807,required=False)
class ExceptionalRecoveryReviewInput(StrictSerializer):
    decision=serializers.ChoiceField(choices=['approve','reject','revoke'])
    rationale=serializers.CharField(max_length=2000)
    verification_reference=serializers.CharField(max_length=250)


class RecoveryRequests(Private):
    @extend_schema(parameters=[ExceptionalRecoveryPageInput],responses=OpenApiTypes.OBJECT)
    def get(self,request):
        form=ExceptionalRecoveryPageInput(data=request.query_params);form.is_valid(raise_exception=True)
        institutions=Institution.objects.filter(pk__in=managed_institutions(request.user))
        query=ExceptionalMFARecovery.objects.filter(institution__in=institutions).select_related('target','requested_by','reviewed_by')
        if 'before' in form.validated_data:query=query.filter(pk__lt=form.validated_data['before'])
        values=list(query.order_by('-pk')[:51])
        return Response({'enabled':settings.EXCEPTIONAL_MFA_RECOVERY_ENABLED,'institutions':list(institutions.values('id','name')),'results':[row(v) for v in values[:50]],'next_before':values[49].pk if len(values)>50 else None})

    @extend_schema(request=ExceptionalRecoveryInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request):
        enabled();form=ExceptionalRecoveryInput(data=request.data);form.is_valid(raise_exception=True);data=form.validated_data
        # Serialize the requester's idempotency keys without locking unrelated services.
        # The requester lock also protects idempotency keys across institutional scopes.
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        device=recent(request,data['institution'])
        target=get_object_or_404(get_user_model(),username=data['username'],institutionmember__institution_id=data['institution'])
        if target.pk==request.user.pk:raise ValidationError('Otra persona debe solicitar la recuperación.')
        eligible(target,data['institution'])
        target_device=get_object_or_404(MFADevice,user=target)
        if not target_device.enabled and not target_device.recovery_required:raise ValidationError('La cuenta no tiene un autenticador que recuperar.')
        existing=ExceptionalMFARecovery.objects.filter(requested_by=request.user,client_key=data['client_key']).first()
        if existing:
            if (existing.target_id,existing.institution_id,existing.rationale,existing.verification_reference)!=(target.pk,data['institution'],data['rationale'],data['verification_reference']):raise Conflict()
            return Response(row(existing))
        value=ExceptionalMFARecovery.objects.create(institution_id=data['institution'],target=target,requested_by=request.user,client_key=data['client_key'],expected_generation=target_device.generation,requester_generation=device.generation,rationale=data['rationale'],verification_reference=data['verification_reference'],expires_at=timezone.now()+timedelta(hours=24))
        record(request.user,data['institution'],'mfa.recovery_requested',value.pk,data['rationale'])
        return Response(row(value),status=201)


class RecoveryReview(Private):
    @extend_schema(request=ExceptionalRecoveryReviewInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    @sensitive_variables()
    def post(self,request,pk):
        enabled();form=ExceptionalRecoveryReviewInput(data=request.data);form.is_valid(raise_exception=True);data=form.validated_data
        initial=get_object_or_404(ExceptionalMFARecovery,pk=pk,institution_id__in=managed_institutions(request.user))
        # Same target-user lock as MFA enrollment/verification/redemption.
        get_user_model().objects.select_for_update().get(pk=initial.target_id)
        value=ExceptionalMFARecovery.objects.select_for_update(of=('self',)).select_related('target','requested_by','reviewed_by').get(pk=pk)
        reviewer=recent(request,value.institution_id)
        if request.user.pk==value.target_id:raise PermissionDenied('El titular no puede decidir su recuperación.')
        decision=data['decision']
        if decision=='revoke':
            if value.state not in {'approved','consumed'}:raise Conflict()
            if value.state=='consumed':
                device=MFADevice.objects.get(user=value.target)
                if device.recovery_required and device.generation==value.approved_generation+1:
                    device.recovery_session_hash='';device.generation+=1;device.save()
            value.state='revoked';value.token_hash='';value.save(update_fields=['state','token_hash'])
            record(request.user,value.institution_id,'mfa.recovery_revoked',value.pk,data['rationale']+' Referencia: '+data['verification_reference'])
            return Response(row(value))
        if request.user.pk==value.requested_by_id:raise PermissionDenied('La revisión debe realizarla otra persona.')
        if value.state!='pending':raise Conflict()
        token=None
        if decision=='approve':
            if value.expires_at<=timezone.now():raise ValidationError('La solicitud venció; registre una nueva.')
            authority(value.requested_by,value.institution_id,value.requester_generation)
            eligible(value.target,value.institution_id)
            device=MFADevice.objects.get(user=value.target)
            if device.generation!=value.expected_generation:raise Conflict()
            device.generation+=1;device.recovery_required=True;device.recovery_session_hash=''
            device.secret='';device.recovery_hashes=[];device.pending_secret='';device.pending_nonce='';device.pending_until=None
            device.save()
            value.approved_generation=device.generation;value.reviewer_generation=reviewer.generation
            token=secrets.token_urlsafe(32);value.token_hash=hashlib.sha256(token.encode()).hexdigest()
            value.expires_at=timezone.now()+timedelta(minutes=30);value.state='approved'
            event(value.target,'mfa.exceptional_authorized')
        else:value.state='rejected'
        value.reviewed_by=request.user;value.review_reason=data['rationale'];value.review_reference=data['verification_reference'];value.reviewed_at=timezone.now();value.save()
        record(request.user,value.institution_id,'mfa.recovery_'+value.state,value.pk,data['rationale']+' Referencia: '+data['verification_reference'])
        response=row(value)
        if token:response['recovery_token']=f'{value.pk}.{token}'
        return Response(response)


@sensitive_variables()
def redeem(request,user,device,password,code):
    """Caller holds the target-user lock. Return false for all unusable credentials."""
    enabled()
    if not user.check_password(password):return False
    parts=code.split('.',1)
    if len(parts)!=2 or not parts[0].isascii() or not parts[0].isdigit() or len(parts[0])>18:return False
    value=ExceptionalMFARecovery.objects.select_for_update(of=('self',)).select_related('requested_by','reviewed_by').filter(pk=int(parts[0]),target=user,state='approved').first()
    if not value or value.expires_at<=timezone.now() or not hmac.compare_digest(value.token_hash,hashlib.sha256(parts[1].encode()).hexdigest()):return False
    if not device.recovery_required or device.generation!=value.approved_generation:return False
    eligible(user,value.institution_id)
    authority(value.requested_by,value.institution_id,value.requester_generation)
    authority(value.reviewed_by,value.institution_id,value.reviewer_generation)
    nonce=secrets.token_hex(32)
    device.enabled=False;device.generation+=1;device.recovery_session_hash=hashlib.sha256(nonce.encode()).hexdigest()
    request.session.cycle_key();request.session['exceptional_recovery_nonce']=nonce
    request.session['exceptional_recovery_request']=value.pk
    value.state='consumed';value.token_hash='';value.consumed_at=timezone.now();value.save(update_fields=['state','token_hash','consumed_at'])
    event(user,'mfa.exceptional_redeemed')
    return True


def complete(request,user,device):
    """Complete only the grant bound to this enrollment session, under target-user lock."""
    value=get_object_or_404(ExceptionalMFARecovery,pk=request.session.get('exceptional_recovery_request'),target=user,state='consumed',approved_generation=device.generation-1)
    eligible(user,value.institution_id)
    authority(value.requested_by,value.institution_id,value.requester_generation)
    authority(value.reviewed_by,value.institution_id,value.reviewer_generation)
    value.state='completed';value.completed_at=timezone.now();value.save(update_fields=['state','completed_at'])
    record(user,value.institution_id,'mfa.recovery_completed',value.pk,'Nuevo autenticador confirmado por el titular.')
    request.session.pop('exceptional_recovery_request',None)
