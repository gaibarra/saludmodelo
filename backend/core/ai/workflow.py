"""Queued, opt-in AI requests. No implicit provider fallback or clinical data release."""
import hashlib
from datetime import timedelta,date
from decimal import Decimal,InvalidOperation,ROUND_CEILING
from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError,PermissionDenied
from core.access import scopes,require,WRITE,REVIEW
from core.models import AIServicePolicy,AIFragmentRelease,AIAnswerRelease,AIRequest,EvidenceFragment,Answer,QuestionnaireInstance,AuditEvent
from core.workflow import save_answer,Conflict
from .contracts import validate_result,validate_action,ACTION_INSTRUCTIONS
from .providers import invoke,ProviderFailure

def allowed_fragments(user,instance,provider):
    today=timezone.localdate()
    require(user,instance.service_id,WRITE)
    permitted=AIFragmentRelease.objects.filter(provider=provider,classification__in=['public','reviewed_anonymized'],expires__gte=today,revoked_at__isnull=True).values_list('fragment_id',flat=True)
    # Select by scope before composing context. No cross-service search or cache.
    return EvidenceFragment.objects.filter(pk__in=permitted,extraction__state='ready',extraction__document__answer__instance=instance,extraction__document__state='accepted').select_related('extraction__document__revision')

def review_release(release_id,answer,provider,purpose='review'):
    release=AIAnswerRelease.objects.select_related('revision','reviewer').filter(pk=release_id,purpose=purpose,revision__answer=answer,provider=provider,answer_etag=answer.etag,revision__version=answer.version,expires__gte=timezone.localdate(),revoked_at__isnull=True,classification__in=['public','reviewed_anonymized']).first()
    if not release or not release.reviewer.is_active or release.reviewer_id==release.revision.author_id:raise ValidationError('La respuesta no tiene autorización vigente para este proveedor y versión.')
    require(release.reviewer,answer.instance.service_id,REVIEW)
    if hashlib.sha256(release.revision.content.encode()).hexdigest()!=release.content_sha256:raise ValidationError('El texto autorizado cambió.')
    return release

def context_for(request):
    instance=request.instance
    if request.action not in ACTION_INSTRUCTIONS:raise ValidationError('Acción no admitida.')
    if request.action=='contradictions' and len(set(request.references))<2:raise ValidationError('Seleccione al menos dos fragmentos distintos para comparar.')
    if request.action in {'suggest','extract','report'} and not request.references:raise ValidationError('Seleccione evidencia autorizada.')
    if not AIServicePolicy.objects.filter(service=instance.service,enabled=True,providers__contains=[request.provider],actions__contains=[request.action]).exists():raise ValidationError('Acción no autorizada por la política vigente.')
    if not request.requested_by.is_active:raise ValidationError('Cuenta inactiva.')
    require(request.requested_by,instance.service_id,WRITE)
    answer=Answer.objects.get(instance=instance)
    if not instance.published:raise ValidationError('Pregunta no publicada.')
    if answer.etag!=request.answer_etag:raise Conflict()
    rows={f.pk:f for f in allowed_fragments(request.requested_by,instance,request.provider).filter(pk__in=request.references)}
    if set(rows)!=set(request.references):raise ValidationError('Algún fragmento ya no está autorizado.')
    fragments={}
    for pk,f in rows.items():
        doc=f.extraction.document;review=doc.reviews.order_by('-id').first()
        if doc.revision.version!=answer.version or not review or review.decision!='accepted' or review.valid_until is None or review.valid_until<timezone.localdate():raise ValidationError('Revise la vigencia y versión de la evidencia.')
        if (doc.scan_required or doc.format not in {'txt','csv'}) and doc.security_state!='clean':raise ValidationError('El análisis de seguridad no permite usar esta evidencia.')
        if f.method=='ocr' and not review.ocr_checked:raise ValidationError('OCR sin cotejo.')
        fragments[pk]={'id':pk,'text':f.text,'locator':f.locator,'sha256':doc.sha256}
    source=instance.question_version
    context={'action':request.action,'task_instructions':ACTION_INSTRUCTIONS[request.action],'question_id':source.question.stable_id,'question_version':source.version,'question':source.source.text,'fragments':list(fragments.values())}
    if request.action=='review' or (request.action=='interview' and request.answer_release_id):
        release=review_release(request.answer_release_id,answer,request.provider,request.action)
        context['answer']={'version':release.revision.version,'text':release.revision.content}
        if request.action=='interview':context['answer']['knowledge']=release.revision.knowledge
    elif request.answer_release_id:raise ValidationError('Esta acción no admite autorización de respuesta.')
    # Other actions omit the answer. All omit usernames, original filenames and raw files.
    return context,fragments

@transaction.atomic
def enqueue(user,instance_id,provider,fragment_ids,version,client_key,action='suggest',answer_release_id=None):
    from django.contrib.auth import get_user_model
    get_user_model().objects.select_for_update().get(pk=user.pk)
    instance=QuestionnaireInstance.objects.select_for_update().get(pk=instance_id)
    require(user,instance.service_id,WRITE)
    if not instance.published:raise ValidationError('La pregunta todavía no está publicada.')
    existing=AIRequest.objects.filter(requested_by=user,client_key=client_key).first()
    if existing:
        if (existing.instance_id,existing.provider,existing.references,existing.answer_etag,existing.action,existing.answer_release_id)!=(instance_id,provider,fragment_ids,version,action,answer_release_id):raise ValidationError('Clave usada para otra solicitud.')
        return existing
    request=AIRequest(instance=instance,requested_by=user,provider=provider,references=fragment_ids,answer_etag=version,client_key=client_key,action=action,answer_release_id=answer_release_id,prompt_version='salud-actions-6')
    context_for(request)
    policy=AIServicePolicy.objects.filter(service=instance.service,enabled=True).first()
    if not policy or provider not in policy.providers:raise ValidationError('No hay política de salida habilitada para este proveedor. Puede continuar con la ayuda revisada.')
    if not getattr(settings,'AI_EXTERNAL_ENABLED',False):raise ValidationError('La salida externa está deshabilitada. Puede continuar manualmente.')
    request.save()
    AuditEvent.objects.create(actor=user,service=instance.service,action='ai.requested',object_id=str(request.pk))
    return request

@transaction.atomic
def claim():
    # A crashed call is uncertain and is never silently replayed or refunded.
    AIRequest.objects.filter(state='running',started_at__lt=timezone.now()-timedelta(minutes=2)).update(state='failed',error='interrupted_uncertain',finished_at=timezone.now())
    request=AIRequest.objects.select_for_update(skip_locked=True).filter(state='pending').order_by('id').first()
    if not request:return None
    request.state='running';request.started_at=timezone.now();request.save(update_fields=['state','started_at'])
    return request.pk

@transaction.atomic
def reserve(request,context):
    import json
    active=AIRequest.objects.select_for_update().get(pk=request.pk)
    if active.state!='running':raise ValidationError('Solicitud cancelada o terminada.')
    policy=AIServicePolicy.objects.select_for_update().get(service=request.instance.service)
    if not policy.enabled or request.provider not in policy.providers or request.action not in policy.actions or not settings.AI_EXTERNAL_ENABLED:raise ValidationError('Salida deshabilitada.')
    provider_config=settings.AI_MODELS.get(request.provider,{})
    if not isinstance(provider_config,dict) or not isinstance(provider_config.get('actions',{}),dict):raise ValidationError('Configuración de acciones inválida.')
    config=provider_config.get('actions',{}).get(request.action,provider_config)
    if not isinstance(config,dict):raise ValidationError('Configuración de modelo inválida.')
    if not config.get('model') or not config.get('max_output_tokens'):raise ValidationError('Modelo no configurado.')
    if not settings.AI_KEYS.get(request.provider):raise ValidationError('Credenciales no configuradas.')
    try:
        input_rate=Decimal(config['input_per_million']);output_rate=Decimal(config['output_per_million'])
        checked=date.fromisoformat(config['rates_verified_on'])
        if not input_rate.is_finite() or not output_rate.is_finite() or min(input_rate,output_rate)<0 or max(input_rate,output_rate)>1000 or not 0<=(timezone.localdate()-checked).days<=30:raise ValueError()
    except (KeyError,ValueError,InvalidOperation,TypeError):raise ValidationError('Tarifas no verificadas o inválidas.')
    maximum=config['max_output_tokens']
    if type(maximum)!=int or not 256<=maximum<=4000:raise ValidationError('Límite de salida inválido.')
    tokens=len(json.dumps(context,ensure_ascii=False).encode())+16000+maximum
    cost=((Decimal(tokens-maximum)*input_rate+Decimal(maximum)*output_rate)/1000000).quantize(Decimal('0.000001'),rounding=ROUND_CEILING)
    now=timezone.localtime();month=now.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
    usage=AIRequest.objects.filter(instance__service=policy.service,started_at__gte=month,reserved_tokens__gt=0)
    if usage.filter(requested_by=request.requested_by).count()>=policy.monthly_user_calls:raise ValidationError('Cuota mensual del usuario agotada.')
    if usage.count()>=policy.monthly_calls or (usage.aggregate(total=Sum('reserved_tokens'))['total'] or 0)+tokens>policy.monthly_tokens:raise ValidationError('Cuota mensual agotada.')
    if policy.monthly_cost_limit<=0 or (usage.aggregate(total=Sum('reserved_cost'))['total'] or Decimal(0))+cost>policy.monthly_cost_limit:raise ValidationError('Presupuesto mensual agotado.')
    recent=usage.filter(provider=request.provider,state='failed',finished_at__gte=now-timedelta(minutes=5)).count()
    if recent>=3:raise ValidationError('Proveedor temporalmente suspendido tras fallos.')
    request.reserved_tokens=tokens;request.model=config['model'];request.reserved_cost=cost;request.rate_snapshot={'input_per_million':str(input_rate),'output_per_million':str(output_rate),'rates_verified_on':config['rates_verified_on']}
    request.save(update_fields=['reserved_tokens','model','reserved_cost','rate_snapshot'])
    return maximum

def process_one():
    pk=claim()
    if pk is None:return False
    request=AIRequest.objects.select_related('instance__question_version__question','instance__question_version__source','requested_by').get(pk=pk)
    try:
        context,fragments=context_for(request)
        maximum=reserve(request,context)
        key=settings.AI_KEYS.get(request.provider,'')
        output=invoke(request.provider,key,request.model,context,max_output=maximum)
        cost=((Decimal(output['input_tokens'])*Decimal(request.rate_snapshot['input_per_million'])+Decimal(output['output_tokens'])*Decimal(request.rate_snapshot['output_per_million']))/1000000).quantize(Decimal('0.000001'),rounding=ROUND_CEILING)
        request.estimated_cost=cost
        if cost>request.reserved_cost or output['input_tokens']+output['output_tokens']>request.reserved_tokens:
            AIServicePolicy.objects.filter(service=request.instance.service).update(enabled=False)
            raise ProviderFailure('usage_exceeded_reservation')
        result=validate_action(validate_result(output['result'],context['question_id'],context['question_version'],fragments),request.action)
        # Recheck access and source state before retaining or exposing a response.
        request.requested_by.refresh_from_db()
        request.instance.refresh_from_db()
        context_for(request)
        if not settings.AI_EXTERNAL_ENABLED or not AIServicePolicy.objects.filter(service=request.instance.service,enabled=True,providers__contains=[request.provider]).exists():raise ValidationError('Política retirada.')
        request.result=result.model_dump();request.input_tokens=output['input_tokens'];request.output_tokens=output['output_tokens'];request.latency_ms=output['latency_ms'];request.state='ready'
    except ProviderFailure as error:request.state='failed';request.error=error.code
    except (ValidationError,PermissionDenied,ValueError,Conflict,Answer.DoesNotExist,AIServicePolicy.DoesNotExist):request.state='failed';request.error='policy_or_validation_failed'
    request.finished_at=timezone.now()
    # Ignore a late completion if recovery already marked the call uncertain.
    AIRequest.objects.filter(pk=pk,state='running').update(state=request.state,error=request.error,result=request.result,input_tokens=request.input_tokens,output_tokens=request.output_tokens,latency_ms=request.latency_ms,estimated_cost=request.estimated_cost,finished_at=request.finished_at)
    return True

@transaction.atomic
def apply(user,request_id):
    request=AIRequest.objects.select_for_update().select_related('instance__question_version__question','instance__question_version__source','requested_by').get(pk=request_id,requested_by=user)
    if request.applied_revision_id:return request.applied_revision.answer
    if request.state!='ready':raise ValidationError('La propuesta no está disponible.')
    context,fragments=context_for(request)
    result=validate_action(validate_result(request.result,context['question_id'],context['question_version'],fragments),request.action)
    if request.action!='suggest':raise ValidationError('Esta acción no permite reemplazar la respuesta.')
    if len(result.suggested_fields)!=1:raise ValidationError('Esta salida sólo pide aclaraciones; no contiene una respuesta propuesta.')
    answer=Answer.objects.get(instance=request.instance)
    answer=save_answer(user,answer.pk,request.answer_etag,result.suggested_fields[0].value,'unconfirmed')
    request.applied_revision=answer.revisions.get(version=answer.version);request.state='applied';request.save(update_fields=['applied_revision','state'])
    AuditEvent.objects.create(actor=user,service=request.instance.service,action='ai.proposal_applied',object_id=str(request.pk))
    return answer
