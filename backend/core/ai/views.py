from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from core.models import *
from core.access import require,scopes,WRITE,REVIEW,READ
from core.governance import managed_services
from core.admin_serializers import StrictSerializer
from core.serializers import AnswerSerializer
from .contracts import ACTION_INSTRUCTIONS
from .workflow import enqueue,apply,allowed_fragments,context_for,review_release

class AIRequestInput(StrictSerializer):
    answer_release_id=serializers.IntegerField(min_value=1,required=False)
    confirm_answer_send=serializers.BooleanField(default=False)
    def validate(self,data):
        if data['action']=='review' and (not data.get('answer_release_id') or not data['confirm_answer_send']):raise serializers.ValidationError('Confirme el envío de la respuesta autorizada.')
        if data.get('answer_release_id') and not data['confirm_answer_send']:raise serializers.ValidationError('Confirme el envío del antecedente autorizado.')
        if data['confirm_answer_send'] and not data.get('answer_release_id'):raise serializers.ValidationError('Seleccione una autorización vigente.')
        if data['action'] not in {'review','interview'} and (data.get('answer_release_id') or data['confirm_answer_send']):raise serializers.ValidationError('Esta acción no envía respuestas.')
        return data
    action=serializers.ChoiceField(choices=list(ACTION_INSTRUCTIONS),default='suggest')
    provider=serializers.ChoiceField(choices=['openai','deepseek'])
    fragment_ids=serializers.ListField(child=serializers.IntegerField(min_value=1),min_length=0,max_length=8)
    version=serializers.IntegerField(min_value=0)
    client_key=serializers.UUIDField()
class AIPolicyInput(StrictSerializer):
    actions=serializers.ListField(child=serializers.ChoiceField(choices=list(ACTION_INSTRUCTIONS)),max_length=7,required=False)
    version=serializers.IntegerField(min_value=0)
    enabled=serializers.BooleanField()
    providers=serializers.ListField(child=serializers.ChoiceField(choices=['openai','deepseek']),max_length=2)
    monthly_user_calls=serializers.IntegerField(min_value=0,max_value=10000)
    monthly_calls=serializers.IntegerField(min_value=0,max_value=10000)
    monthly_tokens=serializers.IntegerField(min_value=0,max_value=100000000)
    monthly_cost_limit=serializers.DecimalField(max_digits=12,decimal_places=6,min_value=0)
    rationale=serializers.CharField(max_length=5000)
class AIReleaseInput(StrictSerializer):
    fragment_ids=serializers.ListField(child=serializers.IntegerField(min_value=1),min_length=1,max_length=8)
    provider=serializers.ChoiceField(choices=['openai','deepseek'])
    classification=serializers.ChoiceField(choices=['public','reviewed_anonymized'])
    expires=serializers.DateField()
    rationale=serializers.CharField(max_length=5000)
class PrivateView(APIView):
    def finalize_response(self,request,response,*args,**kwargs):
        response=super().finalize_response(request,response,*args,**kwargs);response['Cache-Control']='private, no-store';return response
class PolicyView(PrivateView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,service):
        get_object_or_404(managed_services(request.user),pk=service)
        return Response(AIServicePolicy.objects.filter(service_id=service).values('etag','enabled','providers','actions','monthly_calls','monthly_user_calls','monthly_tokens','monthly_cost_limit','rationale').first() or {'etag':0,'enabled':False,'actions':['suggest'],'providers':[],'monthly_calls':0,'monthly_user_calls':0,'monthly_tokens':0,'monthly_cost_limit':'0','rationale':''})
    @extend_schema(request=AIPolicyInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,service):
        get_object_or_404(managed_services(request.user),pk=service)
        service=Service.objects.select_for_update().get(pk=service)
        s=AIPolicyInput(data=request.data);s.is_valid(raise_exception=True);data=s.validated_data
        policy=AIServicePolicy.objects.filter(service=service).first()
        from core.workflow import Conflict
        if data.pop('version')!=(policy.etag if policy else 0):raise Conflict()
        if data['enabled'] and (not data['providers'] or not data.get('actions',policy.actions if policy else ['suggest']) or min(data['monthly_calls'],data['monthly_user_calls'],data['monthly_tokens'],data['monthly_cost_limit'])<=0):raise serializers.ValidationError('Defina proveedores y límites positivos antes de habilitar.')
        if policy:
            for key,value in data.items():setattr(policy,key,value)
            policy.etag+=1;policy.approved_by=request.user;policy.save()
        else:policy=AIServicePolicy.objects.create(service=service,approved_by=request.user,etag=1,**data)
        GovernanceEvent.objects.create(institution=service.site.campus.institution,service=service,actor=request.user,action='ai.policy_changed',object_id=str(policy.pk),rationale=str(request.data))
        return self.get(request,service.pk)
class ReleaseView(PrivateView):
    @extend_schema(request=AIReleaseInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,instance):
        instance=get_object_or_404(QuestionnaireInstance,pk=instance,service_id__in=scopes(request.user,REVIEW))
        s=AIReleaseInput(data=request.data);s.is_valid(raise_exception=True);data=s.validated_data
        if data['expires']<timezone.localdate():raise serializers.ValidationError('La autorización ya estaría vencida.')
        ids=set(data.pop('fragment_ids'));fragments=list(EvidenceFragment.objects.filter(pk__in=ids,extraction__document__answer__instance=instance).select_related('extraction__document__revision'))
        if len(fragments)!=len(ids):raise serializers.ValidationError('Fragmentos fuera del contexto autorizado.')
        for fragment in fragments:
            doc=fragment.extraction.document
            if request.user.pk in {doc.uploader_id,doc.revision.author_id}:raise serializers.ValidationError('Otra persona debe revisar la clasificación y anonimización.')
            if doc.state!='accepted' or fragment.extraction.state!='ready':raise serializers.ValidationError('Primero revise y acepte el documento.')
            release=AIFragmentRelease.objects.create(fragment=fragment,reviewer=request.user,**data)
            AuditEvent.objects.create(actor=request.user,service=instance.service,action='ai.fragment_released',object_id=str(release.pk))
        return Response({'released':len(fragments)},status=201)
class ReleaseRevokeView(PrivateView):
    @extend_schema(request=None,responses=OpenApiTypes.OBJECT)
    def post(self,request,pk):
        release=get_object_or_404(AIFragmentRelease,pk=pk,fragment__extraction__document__answer__instance__service_id__in=scopes(request.user,REVIEW))
        if release.revoked_at is None:
            release.revoked_at=timezone.now();release.save(update_fields=['revoked_at'])
            AuditEvent.objects.create(actor=request.user,service=release.fragment.extraction.document.answer.instance.service,action='ai.release_revoked',object_id=str(release.pk))
        return Response({'revoked':True})
class AssistantView(PrivateView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,instance):
        from django.conf import settings
        instance=get_object_or_404(QuestionnaireInstance,pk=instance,service_id__in=scopes(request.user,WRITE))
        policy=AIServicePolicy.objects.filter(service=instance.service,enabled=True).first()
        providers=policy.providers if policy and settings.AI_EXTERNAL_ENABLED else []
        return Response({'providers':providers,'actions':policy.actions if providers else [],'static_help':instance.published_help.content if instance.published_help else {},'fragments':{p:[{'id':f.pk,'locator':f.locator,'text':f.text} for f in allowed_fragments(request.user,instance,p)[:50]] for p in providers},'requests':list(AIRequest.objects.filter(instance=instance,requested_by=request.user).order_by('-id').values('id','state','error','action')[:20])})
    @extend_schema(request=AIRequestInput,responses=OpenApiTypes.OBJECT)
    def post(self,request,instance):
        get_object_or_404(QuestionnaireInstance,pk=instance,service_id__in=scopes(request.user,WRITE))
        s=AIRequestInput(data=request.data);s.is_valid(raise_exception=True);data=s.validated_data
        job=enqueue(request.user,instance,data['provider'],data['fragment_ids'],data['version'],data['client_key'],data['action'],data.get('answer_release_id'))
        return Response({'id':job.pk,'state':job.state},status=202)
class ResultView(PrivateView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,pk):
        job=get_object_or_404(AIRequest,pk=pk,requested_by=request.user,instance__service_id__in=scopes(request.user,WRITE))
        if job.state=='ready':context_for(job)
        return Response({'id':job.pk,'action':job.action,'reviewed_version':job.answer_release.revision.version if job.action=='review' and job.answer_release_id else None,'state':job.state,'error':job.error,'result':job.result if job.state=='ready' else None,'model':job.model,'provider':job.provider,'input_tokens':job.input_tokens,'output_tokens':job.output_tokens,'estimated_cost':job.estimated_cost})
    @extend_schema(request=None,responses=AnswerSerializer)
    def post(self,request,pk):
        get_object_or_404(AIRequest,pk=pk,requested_by=request.user,instance__service_id__in=scopes(request.user,WRITE))
        answer=apply(request.user,pk)
        return Response(AnswerSerializer(answer,context={'request':request}).data)

class AIDecisionInput(StrictSerializer):
    decision=serializers.ChoiceField(choices=['cancel','reject'])
class DecisionView(PrivateView):
    @extend_schema(request=AIDecisionInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,pk):
        job=get_object_or_404(AIRequest.objects.select_for_update(),pk=pk,requested_by=request.user,instance__service_id__in=scopes(request.user,WRITE))
        s=AIDecisionInput(data=request.data);s.is_valid(raise_exception=True);decision=s.validated_data['decision']
        target='cancelled' if decision=='cancel' else 'rejected'
        if job.state==target:return Response({'id':job.pk,'state':job.state})
        if decision=='cancel' and job.state not in ['pending','running']:raise serializers.ValidationError('Sólo puede cancelar una solicitud en proceso.')
        if decision=='reject' and job.state!='ready':raise serializers.ValidationError('Sólo puede rechazar una propuesta disponible.')
        job.state=target;job.finished_at=timezone.now()
        if target=='cancelled':job.result=None
        job.save(update_fields=['state','finished_at','result'])
        AuditEvent.objects.create(actor=request.user,service=job.instance.service,action='ai.'+target,object_id=str(job.pk))
        return Response({'id':job.pk,'state':job.state})

class AnswerReleaseInput(StrictSerializer):
    purpose=serializers.ChoiceField(choices=['review','interview'],default='review')
    version=serializers.IntegerField(min_value=0)
    provider=serializers.ChoiceField(choices=['openai','deepseek'])
    classification=serializers.ChoiceField(choices=['public','reviewed_anonymized'])
    expires=serializers.DateField()
    rationale=serializers.CharField(max_length=5000)
    checked=serializers.BooleanField()

class AnswerReleaseView(PrivateView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,instance):
        instance=get_object_or_404(QuestionnaireInstance,pk=instance,service_id__in=scopes(request.user,READ))
        answer=Answer.objects.get(instance=instance)
        revision=answer.revisions.filter(version=answer.version).first()
        releases=[]
        for release in AIAnswerRelease.objects.filter(revision__answer=answer).order_by('-id')[:50]:
            valid=False
            try:
                review_release(release.pk,answer,release.provider,release.purpose);valid=instance.published
            except (serializers.ValidationError,PermissionDenied):pass
            releases.append({'id':release.pk,'purpose':release.purpose,'provider':release.provider,'version':release.revision.version,'expires':release.expires,'revoked':release.revoked_at is not None,'usable':valid})
        return Response({'version':answer.etag,'revision':answer.version,'text':revision.content if revision else '', 'can_revoke':scopes(request.user,REVIEW).filter(service_id=instance.service_id).exists(),'can_release':scopes(request.user,REVIEW).filter(service_id=instance.service_id).exists() and bool(revision) and revision.author_id!=request.user.pk,'releases':releases})
    @extend_schema(request=AnswerReleaseInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,instance):
        import hashlib
        from core.workflow import Conflict
        instance=get_object_or_404(QuestionnaireInstance.objects.select_for_update(),pk=instance,service_id__in=scopes(request.user,REVIEW))
        require(request.user,instance.service_id,REVIEW)
        answer=Answer.objects.select_for_update().get(instance=instance)
        s=AnswerReleaseInput(data=request.data);s.is_valid(raise_exception=True);data=s.validated_data
        if data.pop('version')!=answer.etag:raise Conflict()
        if not instance.published or not data.pop('checked') or data['expires']<timezone.localdate():raise serializers.ValidationError('Revise publicación, clasificación y vigencia.')
        revision=answer.revisions.filter(version=answer.version).first()
        if not revision or not revision.content.strip():raise serializers.ValidationError('Primero guarde una respuesta no vacía.')
        if revision.author_id==request.user.pk:raise serializers.ValidationError('Otra persona debe revisar la salida del texto.')
        release=AIAnswerRelease.objects.create(revision=revision,answer_etag=answer.etag,content_sha256=hashlib.sha256(revision.content.encode()).hexdigest(),reviewer=request.user,**data)
        AuditEvent.objects.create(actor=request.user,service=instance.service,action='ai.answer_released',object_id=str(release.pk))
        return Response({'id':release.pk},status=201)

class AnswerReleaseRevokeView(PrivateView):
    @extend_schema(request=None,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,pk):
        release=get_object_or_404(AIAnswerRelease.objects.select_for_update(),pk=pk,revision__answer__instance__service_id__in=scopes(request.user,REVIEW))
        if release.revoked_at is None:
            release.revoked_at=timezone.now();release.save(update_fields=['revoked_at'])
            AuditEvent.objects.create(actor=request.user,service=release.revision.answer.instance.service,action='ai.answer_release_revoked',object_id=str(release.pk))
        return Response({'revoked':True})
