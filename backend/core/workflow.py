from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError,APIException
from .models import *
from .access import require,WRITE,REVIEW
class Conflict(APIException):
    status_code=409
    default_detail='Otra persona cambió este registro. Recargue y compare antes de guardar.'
def audit(user,answer,action):
    AuditEvent.objects.create(actor=user,service=answer.instance.service,action=action,object_id=str(answer.pk))
@transaction.atomic
def save_answer(user,answer_id,expected,content,knowledge):
    instance_id=Answer.objects.values_list('instance_id',flat=True).get(pk=answer_id)
    QuestionnaireInstance.objects.select_for_update().get(pk=instance_id)
    a=Answer.objects.select_for_update(of=('self',)).select_related('instance').get(pk=answer_id)
    require(user,a.instance.service_id,WRITE)
    if a.etag!=expected: raise Conflict()
    if not a.instance.published: raise ValidationError('La pregunta aún no está publicada.')
    if a.state in ['submitted','in_review']: raise ValidationError('Espere la revisión antes de corregir.')
    a.version+=1;a.etag+=1;a.state='draft';a.save()
    AnswerRevision.objects.create(answer=a,version=a.version,author=user,content=content,knowledge=knowledge,help_revision=a.instance.published_help)
    if knowledge in ['unknown','absent','unconfirmed','not_applicable']:
        t,_=Task.objects.get_or_create(deduplication_key=f'answer:{a.pk}:knowledge:{knowledge}',defaults={'service':a.instance.service,'answer':a,'owner':user,'title':'Revisar aplicabilidad' if knowledge=='not_applicable' else 'Confirmar información pendiente'})
        OutboxEvent.objects.get_or_create(key=f'task:{t.pk}',defaults={'task':t})
    audit(user,a,'answer.saved');return a
@transaction.atomic
def transition(user,answer_id,expected,target,rationale):
    instance_id=Answer.objects.values_list('instance_id',flat=True).get(pk=answer_id)
    QuestionnaireInstance.objects.select_for_update().get(pk=instance_id)
    a=Answer.objects.select_for_update(of=('self',)).select_related('instance').get(pk=answer_id)
    require(user,a.instance.service_id,WRITE if target=='submitted' else REVIEW)
    if a.etag!=expected: raise Conflict()
    if not a.instance.published:raise ValidationError('Publique y revise la pregunta vigente antes de enviar respuestas.')
    r=a.revisions.get(version=a.version)
    if r.help_revision_id!=a.instance.published_help_id:raise ValidationError('Guarde una nueva versión de respuesta con la ayuda vigente.')
    if target=='submitted':
        if a.state not in ['draft','returned'] or not r.content.strip(): raise ValidationError('Complete la respuesta antes de enviarla.')
    else:
        if a.state not in ['submitted','in_review']: raise ValidationError('Esta respuesta no está enviada a revisión.')
        if r.author_id==user.pk: raise ValidationError('La revisión requiere otra persona.')
        if not rationale.strip(): raise ValidationError('Indique el fundamento de la revisión.')
        if target=='validated' and r.knowledge!='known': raise ValidationError('Resuelva el pendiente o la aplicabilidad mediante su flujo competente antes de validar.')
        Review.objects.create(revision=r,reviewer=user,decision=target,rationale=rationale)
    a.state=target;a.etag+=1;a.save();audit(user,a,'answer.'+target);return a
