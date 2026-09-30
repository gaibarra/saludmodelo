"""Explicit administrative requests; originals and independently saved reports stay intact."""
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied,ValidationError
from core.access import scopes
from core.governance import managed_services
from core.models import AdministrativeTimeCorrection,Service,Task,TimeEntry,TimeCorrection
from core.time_accounting import total
from core.workflow import Conflict
from .workflow import event


def authorized(user,service):
    return bool(get_user_model().objects.filter(pk=user.pk,is_active=True).exists() and
                service in scopes(user) and managed_services(user).filter(pk=service).exists())


def require_authority(user,service):
    if not authorized(user,service):
        raise PermissionDenied('Requiere Dirección con lectura vigente del servicio y cuenta activa.')


def lock_entry(entry_id):
    original=get_object_or_404(TimeEntry,pk=entry_id)
    Service.objects.select_for_update().get(pk=original.task.service_id)
    task=Task.objects.select_for_update().get(pk=original.task_id)
    # Same person lock as self-corrections/new entries, including across services.
    get_user_model().objects.select_for_update().get(pk=original.actor_id)
    entry=TimeEntry.objects.select_for_update().get(pk=entry_id)
    return task,entry


def current(entry):
    latest=entry.corrections.order_by('-version').first()
    return (latest.version,latest.minutes) if latest else (0,entry.minutes)


@transaction.atomic
def propose(user,entry_id,version,minutes,rationale,client_key):
    initial=get_object_or_404(TimeEntry,pk=entry_id,task__service_id__in=scopes(user))
    require_authority(user,initial.task.service_id)
    task,entry=lock_entry(entry_id)
    require_authority(user,task.service_id)
    if entry.actor_id==user.pk:raise ValidationError('Use la corrección de horas propias.')
    existing=AdministrativeTimeCorrection.objects.filter(entry=entry,requested_by=user,client_key=client_key).first()
    if existing:
        if (existing.entry_id,existing.expected_version,existing.minutes,existing.rationale)!=(entry_id,version,minutes,rationale):raise Conflict()
        return existing
    observed,previous=current(entry)
    if version!=observed:raise Conflict()
    if previous==minutes:raise ValidationError('El ajuste debe cambiar los minutos efectivos.')
    request=AdministrativeTimeCorrection.objects.create(entry=entry,requested_by=user,client_key=client_key,expected_version=version,previous_minutes=previous,minutes=minutes,rationale=rationale)
    event(user,task,'time.admin_requested',f'Solicitud {request.pk}; registro {entry.pk}; {previous} → {minutes} minutos. Motivo: {rationale}')
    return request


@transaction.atomic
def decide(user,request_id,approve,rationale):
    initial=get_object_or_404(AdministrativeTimeCorrection,pk=request_id,entry__task__service_id__in=scopes(user))
    require_authority(user,initial.entry.task.service_id)
    task,entry=lock_entry(initial.entry_id)
    request=AdministrativeTimeCorrection.objects.select_for_update().select_related('requested_by').get(pk=request_id)
    require_authority(user,task.service_id)
    if user.pk in [request.requested_by_id,entry.actor_id]:raise ValidationError('La revisión requiere otra persona de Dirección, distinta del solicitante y del autor de las horas.')
    target='approved' if approve else 'rejected'
    if request.state!='pending':
        if (request.state,request.reviewed_by_id,request.review_reason)==(target,user.pk,rationale):return request
        raise Conflict()
    if approve:
        require_authority(request.requested_by,task.service_id)
        version,previous=current(entry)
        if (version,previous)!=(request.expected_version,request.previous_minutes):raise Conflict()
        if total(TimeEntry.objects.filter(actor_id=entry.actor_id,day=entry.day).exclude(pk=entry.pk))+request.minutes>1440:
            raise ValidationError('El tiempo diario supera 24 horas.')
        request.correction=TimeCorrection.objects.create(entry=entry,actor=user,version=version+1,minutes=request.minutes,rationale=request.rationale)
    request.state=target;request.reviewed_by=user;request.review_reason=rationale;request.reviewed_at=timezone.now();request.save()
    event(user,task,'time.admin_'+target,f'Solicitud {request.pk}; registro {entry.pk}; decisión: {rationale}')
    return request


def serialize(request,user):
    entry=request.entry
    return {'id':request.pk,'entry':entry.pk,'author':entry.actor.username,'day':entry.day,'expected_version':request.expected_version,'previous_minutes':request.previous_minutes,'minutes':request.minutes,'rationale':request.rationale,'state':request.state,'requested_by':request.requested_by.username,'reviewed_by':request.reviewed_by.username if request.reviewed_by_id else None,'review_reason':request.review_reason,'created_at':request.created_at,'reviewed_at':request.reviewed_at,'correction':request.correction_id,'can_review':request.state=='pending' and user.pk not in [request.requested_by_id,entry.actor_id] and authorized(user,entry.task.service_id)}
