from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from .models import QuestionnaireInstance, HelpRevision, HelpReview, Answer, AuditEvent
from .access import require, REVIEW
from .governance import EDIT_HELP
from .workflow import Conflict

HELP_FIELDS = ['plain_explanation', 'purpose', 'knower', 'where_to_find', 'steps', 'fictional_example', 'evidence', 'sufficiency', 'applicability', 'escalation']

def complete(content):
    return all(isinstance(content.get(k), str) and content[k].strip() for k in HELP_FIELDS)

def locked(instance_id, expected):
    instance = QuestionnaireInstance.objects.select_for_update(of=('self',)).select_related('service').get(pk=instance_id)
    if expected is not None and instance.etag != expected:
        raise Conflict()
    return instance

def log(user, instance, action, revision):
    AuditEvent.objects.create(actor=user, service=instance.service, action=action, object_id=f'{instance.pk}:help:{revision.pk}')

@transaction.atomic
def save_help(user, instance_id, expected, content, proposal_digest=""):
    instance = locked(instance_id, expected)
    require(user, instance.service_id, EDIT_HELP)
    from .help_drafts import build
    from .models import HelpSourceLink
    proposal=None
    if proposal_digest:
        proposal=build(instance)
        if proposal['digest']!=proposal_digest:
            raise Conflict('La propuesta o sus fuentes cambiaron. Revise otra vista previa antes de guardarla.')
    latest = instance.help_revisions.order_by('-number').first()
    origin='manual' if proposal is None else 'source_draft' if content==proposal['content'] else 'source_draft_edited'
    revision = HelpRevision.objects.create(instance=instance,question_version=instance.question_version, number=latest.number + 1 if latest else 1, author=user, content=content,proposal_digest=proposal_digest,origin=origin)
    if proposal:
        HelpSourceLink.objects.bulk_create([HelpSourceLink(revision=revision,source_id=ref['id']) for ref in proposal['references']])
    instance.etag += 1
    instance.save(update_fields=['etag'])
    log(user, instance, 'help.saved', revision)
    return instance

@transaction.atomic
def review_help(user, instance_id, expected, decision, rationale):
    instance = locked(instance_id, expected)
    require(user, instance.service_id, REVIEW)
    revision = instance.help_revisions.order_by('-number').first()
    if revision is None:
        raise ValidationError('Guarde primero una ficha de ayuda.')
    if revision.question_version_id not in [None,instance.question_version_id]:raise ValidationError('Guarde una ayuda nueva para la fuente vigente.')
    if revision.author_id == user.pk:
        raise ValidationError('Otra persona debe revisar esta ficha.')
    if hasattr(revision, 'review'):
        raise ValidationError('Esta versión ya fue revisada. Una corrección requiere otra versión.')
    if decision == 'approved' and not complete(revision.content):
        raise ValidationError('Complete los diez apartados antes de aprobar la ayuda.')
    HelpReview.objects.create(revision=revision, reviewer=user, decision=decision, rationale=rationale)
    instance.etag += 1
    instance.save(update_fields=['etag'])
    log(user, instance, 'help.' + decision, revision)
    return instance

@transaction.atomic
def publish(user, instance_id, expected=None):
    # Lock service before its questions; scope selection uses the same ordering.
    from .models import Service
    service_id = QuestionnaireInstance.objects.values_list('service_id', flat=True).get(pk=instance_id)
    Service.objects.select_for_update().get(pk=service_id)
    all_instances = list(QuestionnaireInstance.objects.select_for_update().filter(service_id=service_id).order_by('id'))
    instance = locked(instance_id, expected)
    require(user, instance.service_id, REVIEW)
    for other in all_instances:
        latest = other.help_revisions.order_by('-number').first()
        if latest is None or latest.question_version_id not in [None,other.question_version_id] or not complete(latest.content) or not hasattr(latest, 'review') or latest.review.decision != 'approved':
            raise ValidationError('Complete y revise todas las fichas del cuestionario de este servicio antes de publicar.')
    if not instance.service.confirmed:
        raise ValidationError('Confirme primero el alcance del servicio.')
    revision = instance.help_revisions.order_by('-number').first()
    if revision is None or not complete(revision.content) or not hasattr(revision, 'review'):
        raise ValidationError('La ayuda debe estar completa y revisada por otra persona.')
    if revision.review.decision != 'approved' or revision.author_id == revision.review.reviewer_id:
        raise ValidationError('Esta versión de ayuda no está aprobada.')
    if instance.published_help_id == revision.pk and instance.published:
        return instance
    answer = Answer.objects.select_for_update().filter(instance=instance).first()
    if answer is not None and instance.published_help_id is not None:
        # Keep answer revisions and old reviews; explicitly withdraw current validation.
        answer.state = 'draft' if answer.version else 'pending'
        answer.etag += 1
        answer.save(update_fields=['state', 'etag'])
        log(user, instance, 'answer.review_required_after_help_change', revision)
    instance.published_help = revision
    instance.published = True
    instance.etag += 1
    instance.save(update_fields=['published_help', 'published', 'etag'])
    Answer.objects.get_or_create(instance=instance)
    log(user, instance, 'question.published', revision)
    return instance
