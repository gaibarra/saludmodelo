from datetime import date
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied
from .models import ClarificationRequest, ClarificationMessage, QuestionnaireInstance, RoleAssignment, Answer, AuditEvent
from .access import scopes, require, WRITE, REVIEW
from .workflow import Conflict

CONSULT_ROLES=WRITE|REVIEW|{'coordinator'}

def visible(user):
    return ClarificationRequest.objects.filter(instance__service_id__in=scopes(user,CONSULT_ROLES)).filter(Q(opened_by=user)|Q(assigned_to=user))

def recipients(instance,user):
    today=timezone.localdate()
    require(user,instance.service_id,CONSULT_ROLES)
    return RoleAssignment.objects.filter(service=instance.service,user__is_active=True,role__in=REVIEW,starts__lte=today,ends__gte=today,revoked_at__isnull=True).exclude(user=user).select_related('user')

def audit(user,request,action):
    AuditEvent.objects.create(actor=user,service=request.instance.service,action='consultation.'+action,object_id=str(request.pk))

@transaction.atomic
def open_request(user,instance_id,assigned_to,question,due,client_key):
    instance=QuestionnaireInstance.objects.select_for_update().get(pk=instance_id)
    require(user,instance.service_id,CONSULT_ROLES)
    # Serialize idempotent submissions by this sender, also across different questions.
    from django.contrib.auth import get_user_model
    get_user_model().objects.select_for_update().get(pk=user.pk)
    existing=ClarificationRequest.objects.filter(opened_by=user,client_key=client_key).first()
    if existing:
        if (existing.instance_id,existing.assigned_to_id,existing.question,existing.due)!=(instance_id,assigned_to,question,due):
            raise ValidationError('La clave de envío ya se usó para otra consulta.')
        return existing
    if not recipients(instance,user).filter(user_id=assigned_to).exists():
        raise ValidationError('Seleccione otro responsable con permiso de revisión vigente en este servicio.')
    if due<max(date(2026,10,1),timezone.localdate()):
        raise ValidationError('La fecha objetivo no puede ser anterior al inicio del plan ni al día de hoy.')
    answer=Answer.objects.filter(instance=instance).first()
    revision=answer.revisions.filter(version=answer.version).first() if answer else None
    help_revision=instance.published_help or instance.help_revisions.order_by('-number').first()
    request=ClarificationRequest.objects.create(instance=instance,opened_by=user,assigned_to_id=assigned_to,question=question,due=due,client_key=client_key,help_revision=help_revision,answer_revision=revision)
    audit(user,request,'opened')
    return request

@transaction.atomic
def post_message(user,request_id,expected,body,client_key):
    request=ClarificationRequest.objects.select_for_update().get(pk=request_id)
    if not visible(user).filter(pk=request.pk).exists(): raise PermissionDenied('No tiene acceso vigente a esta consulta.')
    if request.assigned_to_id==user.pk: require(user,request.instance.service_id,REVIEW)
    existing=ClarificationMessage.objects.filter(request=request,author=user,client_key=client_key).first()
    if existing:
        if existing.body!=body: raise ValidationError('La clave de envío ya se usó para otro mensaje.')
        return request
    if request.etag!=expected: raise Conflict()
    if request.state=='resolved': raise ValidationError('La consulta está cerrada; abra otra si surge una duda nueva.')
    ClarificationMessage.objects.create(request=request,author=user,body=body,client_key=client_key)
    request.state='answered' if request.assigned_to_id==user.pk else 'open'
    request.etag+=1
    request.save(update_fields=['state','etag','updated_at'])
    audit(user,request,'message_added')
    return request

@transaction.atomic
def resolve(user,request_id,expected,rationale):
    request=ClarificationRequest.objects.select_for_update().get(pk=request_id)
    if not visible(user).filter(pk=request.pk).exists() or user.pk!=request.opened_by_id:
        raise PermissionDenied('Sólo quien abrió la consulta puede confirmar que la duda quedó resuelta.')
    if request.etag!=expected: raise Conflict()
    if request.state!='answered': raise ValidationError('Espere una respuesta del responsable antes de cerrar la consulta.')
    request.resolution=rationale
    request.state='resolved'
    request.etag+=1
    request.save(update_fields=['resolution','state','etag','updated_at'])
    audit(user,request,'resolved')
    return request
