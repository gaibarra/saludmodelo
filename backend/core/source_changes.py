"""Explicit independent approval of question source upgrades."""
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from .capacity import Private
from .models import QuestionnaireInstance,QuestionVersion,QuestionSourceChange,CatalogAccess,Service,Answer,AuditEvent
from .access import scopes,READ
from .governance import require_manage
from .admin_serializers import StrictSerializer
from .workflow import Conflict

def instance_for(user,pk):return get_object_or_404(QuestionnaireInstance.objects.select_related('service__site__campus','question_version'),pk=pk,service_id__in=scopes(user,READ))
def targets(instance):
    batches=CatalogAccess.objects.filter(institution_id=instance.service.site.campus.institution_id).values_list('batch_id',flat=True)
    return QuestionVersion.objects.filter(question_id=instance.question_version.question_id,version__gt=instance.question_version.version,source__batch_id__in=batches).select_related('source').order_by('-version')
def serialize(change):
    return {'from_text':change.source_from.source.text,'to_text':change.source_to.source.text,'from_locator':change.source_from.source.locator,'to_locator':change.source_to.source.locator,'id':change.pk,'state':change.state,'source_from':change.source_from_id,'source_to':change.source_to_id,'requested_by':change.requested_by_id,'reviewed_by':change.reviewed_by_id,'rationale':change.rationale,'review_reason':change.review_reason,'created_at':change.created_at,'reviewed_at':change.reviewed_at}
class SourceInput(StrictSerializer):
    version=serializers.IntegerField(min_value=0)
    target=serializers.IntegerField(min_value=1)
    rationale=serializers.CharField(max_length=3000)
class SourceReviewInput(StrictSerializer):
    approve=serializers.BooleanField()
    rationale=serializers.CharField(max_length=3000)
class SourceChanges(Private):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,pk):
        instance=instance_for(request.user,pk);require_manage(request.user,instance.service)
        return Response({'version':instance.etag,'current':instance.question_version_id,'targets':[{'id':v.pk,'version':v.version,'text':v.source.text,'locator':v.source.locator} for v in targets(instance)],'changes':[serialize(c) for c in instance.source_changes.select_related('source_from__source','source_to__source').order_by('-id')]})
    @extend_schema(request=SourceInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,pk):
        instance=instance_for(request.user,pk)
        Service.objects.select_for_update().get(pk=instance.service_id)
        instance=QuestionnaireInstance.objects.select_for_update().select_related('question_version','service__site__campus').get(pk=pk)
        require_manage(request.user,instance.service)
        instance_for(request.user,pk)
        s=SourceInput(data=request.data);s.is_valid(raise_exception=True);data=s.validated_data
        if instance.etag!=data['version']:raise Conflict()
        target=get_object_or_404(targets(instance),pk=data['target'])
        if instance.source_changes.filter(state='pending').exists():raise serializers.ValidationError('Ya hay una propuesta pendiente de cambio de fuente.')
        change=QuestionSourceChange.objects.create(instance=instance,source_from=instance.question_version,source_to=target,expected_etag=instance.etag,requested_by=request.user,rationale=data['rationale'])
        AuditEvent.objects.create(actor=request.user,service=instance.service,action='question.source_change_requested',object_id=str(change.pk))
        return Response(serialize(change),status=201)
class SourceReview(Private):
    @extend_schema(request=SourceReviewInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,pk):
        original=get_object_or_404(QuestionSourceChange,pk=pk,instance__service_id__in=scopes(request.user,READ))
        Service.objects.select_for_update().get(pk=original.instance.service_id)
        instance=QuestionnaireInstance.objects.select_for_update().select_related('question_version','service__site__campus').get(pk=original.instance_id)
        require_manage(request.user,instance.service);instance_for(request.user,instance.pk)
        change=QuestionSourceChange.objects.select_for_update().get(pk=pk)
        s=SourceReviewInput(data=request.data);s.is_valid(raise_exception=True);data=s.validated_data
        if change.requested_by_id==request.user.pk:raise serializers.ValidationError('Otra persona de Dirección debe revisar el cambio de fuente.')
        if change.state!='pending':raise Conflict()
        if data['approve']:
            if instance.etag!=change.expected_etag or instance.question_version_id!=change.source_from_id:raise Conflict()
            get_object_or_404(targets(instance),pk=change.source_to_id)
            # Backfill only provenance metadata, never the old help/answer contents.
            instance.help_revisions.filter(question_version__isnull=True).update(question_version_id=change.source_from_id)
            answer=Answer.objects.select_for_update().filter(instance=instance).first()
            if answer:
                answer.state='draft' if answer.version else 'pending';answer.etag+=1;answer.save(update_fields=['state','etag'])
            instance.question_version_id=change.source_to_id;instance.published=False;instance.published_help=None;instance.etag+=1;instance.save()
        change.state='approved' if data['approve'] else 'rejected';change.reviewed_by=request.user;change.review_reason=data['rationale'];change.reviewed_at=timezone.now();change.save()
        AuditEvent.objects.create(actor=request.user,service=instance.service,action='question.source_'+change.state,object_id=str(change.pk))
        return Response(serialize(change))
