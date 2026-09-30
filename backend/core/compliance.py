"""Versioned compliance trace. No legal conclusion is inferred from an import."""
from datetime import date
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from .models import *
from .access import scopes,require,READ
from .admin_serializers import StrictSerializer
from .workflow import Conflict
EDIT={'manager','compliance'}
CHECK=EDIT|{'clinical'}
APPROVE={'compliance'}

def catalogs(service):
    return CatalogAccess.objects.filter(institution=service.site.campus.institution).values_list('batch_id',flat=True)
def controls(service):
    return SourceRecord.objects.filter(batch_id__in=catalogs(service),kind='annex',text__regex=r'^C(0[1-9]|1[0-9]|20) ')
def scoped(user,service,roles=READ):
    return get_object_or_404(Service,pk=service,pk__in=scopes(user,roles))
def record_for(user,pk,roles=READ,lock=False):
    query=ComplianceRecord.objects.select_for_update() if lock else ComplianceRecord.objects.all()
    return get_object_or_404(query,pk=pk,service_id__in=scopes(user,roles))
def current(record):return record.revisions.get(version=record.version)
def issues(rev):
    reasons=[];today=timezone.localdate()
    if rev.validity!='verified':reasons.append('Vigencia normativa por verificar o retirada.')
    if not all([rev.numeral.strip(),rev.consulted_version.strip(),rev.official_url,rev.consulted_on]):reasons.append('Falta numeral, versión, fuente oficial o fecha de consulta.')
    if rev.next_review is None or rev.next_review<today:reasons.append('Revisión programada vencida o sin fecha.')
    if rev.applicability=='pending':reasons.append('Aplicabilidad por verificar.')
    if rev.norm.source.batch_id not in catalogs(rev.record.service) or rev.control.batch_id not in catalogs(rev.record.service):reasons.append('Acceso al catálogo retirado.')
    if not RoleAssignment.objects.filter(user=rev.owner,service=rev.record.service,role__in=CHECK,starts__lte=today,ends__gte=today,revoked_at__isnull=True,user__is_active=True).exists():reasons.append('Responsable sin nombramiento vigente.')
    if rev.applicability=='applies':
        answer=Answer.objects.filter(instance=rev.question).first()
        if not answer or not rev.answer_revision_id or answer.version!=rev.answer_revision.version or answer.state!='validated' or not rev.question.published:reasons.append('Respuesta no validada, modificada o pregunta retirada.')
        docs=list(rev.evidence.all())
        if not docs:reasons.append('Falta evidencia aceptada.')
        for doc in docs:
            review=doc.reviews.order_by('-id').first()
            if doc.revision_id!=rev.answer_revision_id or doc.state!='accepted' or not review or review.decision!='accepted' or not review.valid_until or review.valid_until<today:reasons.append('Evidencia desactualizada, devuelta o vencida.');break
            if (doc.scan_required or doc.format not in {'txt','csv'}) and doc.security_state!='clean':reasons.append('Evidencia sin análisis de seguridad limpio.');break
    return reasons

def snapshot(record):
    rev=current(record);review=rev.reviews.order_by('-id').first();test=rev.checks.order_by('-id').first();reasons=issues(rev)
    if rev.applicability=='applies' and (not test or test.result!='passed'):reasons.append('Falta prueba satisfactoria de esta versión.')
    if review and review.decision=='approved' and rev.applicability=='applies' and review.test_id!=(test.pk if test else None):reasons.append('La prueba cambió después de la aprobación.')
    state='draft'
    if review:
        state='returned' if review.decision=='returned' else ('needs_review' if reasons else ('not_applicable_reviewed' if rev.applicability=='not_applies' else 'approved'))
    return {'id':record.pk,'service':record.service_id,'etag':record.etag,'version':record.version,'state':state,'issues':reasons,'revision':revision_data(rev),'tests':list(rev.checks.order_by('-id').values('id','author_id','procedure','expected','observed','result','created_at')),'reviews':list(rev.reviews.order_by('-id').values('id','reviewer_id','decision','rationale','test_id','created_at'))}
def revision_data(rev):
    return {'id':rev.pk,'version':rev.version,'author':rev.author_id,'norm':rev.norm_id,'norm_code':rev.norm.code,'norm_title':rev.norm.title,'source_locator':rev.norm.source.locator,'source_sha256':rev.norm.source.batch.digest,'control':rev.control_id,'control_text':rev.control.text,'process_name':rev.process.name,'question':rev.question_id,'question_text':rev.question.question_version.source.text,'answer_revision':rev.answer_revision_id,'owner':rev.owner_id,'evidence':list(rev.evidence.values_list('pk',flat=True)),**{f:getattr(rev,f) for f in ['nature','numeral','consulted_version','official_url','consulted_on','validity','applicability','applicability_reason','obligation','link_reason','next_review']}}
class ComplianceInput(StrictSerializer):
    version=serializers.IntegerField(min_value=0)
    norm=serializers.IntegerField(min_value=1)
    control=serializers.IntegerField(min_value=1)
    process_name=serializers.CharField(max_length=200)
    question=serializers.IntegerField(min_value=1)
    owner=serializers.IntegerField(min_value=1)
    evidence=serializers.ListField(child=serializers.UUIDField(),max_length=20)
    nature=serializers.ChoiceField(choices=['legal_obligation','recommended_improvement'])
    numeral=serializers.CharField(max_length=160,allow_blank=True)
    consulted_version=serializers.CharField(max_length=200,allow_blank=True)
    official_url=serializers.URLField(max_length=1000,allow_blank=True)
    consulted_on=serializers.DateField(allow_null=True)
    validity=serializers.ChoiceField(choices=['pending','verified','obsolete'])
    applicability=serializers.ChoiceField(choices=['pending','applies','not_applies'])
    applicability_reason=serializers.CharField(max_length=5000)
    obligation=serializers.CharField(max_length=10000)
    link_reason=serializers.CharField(max_length=5000)
    next_review=serializers.DateField(allow_null=True)
    def validate(self,data):
        if data['official_url'] and not data['official_url'].startswith('https://'):raise serializers.ValidationError('Use una fuente HTTPS. El servidor no descarga enlaces.')
        if data['consulted_on'] and data['consulted_on']>timezone.localdate():raise serializers.ValidationError('La consulta no puede estar en el futuro.')
        if data['next_review'] and data['next_review']<max(timezone.localdate(),date(2026,10,1)):raise serializers.ValidationError('Programe una revisión no vencida y no anterior al 1 de octubre de 2026.')
        if data['validity']=='verified' and not all([data['numeral'],data['consulted_version'],data['official_url'],data['consulted_on']]):raise serializers.ValidationError('Documente la verificación de vigencia.')
        return data
class ComplianceCheckInput(StrictSerializer):
    version=serializers.IntegerField(min_value=0)
    procedure=serializers.CharField(max_length=5000)
    expected=serializers.CharField(max_length=5000)
    observed=serializers.CharField(max_length=5000)
    result=serializers.ChoiceField(choices=['passed','failed'])
class ComplianceReviewInput(StrictSerializer):
    version=serializers.IntegerField(min_value=0)
    decision=serializers.ChoiceField(choices=['approved','returned'])
    rationale=serializers.CharField(max_length=5000)
def validated(cls,request):
    s=cls(data=request.data);s.is_valid(raise_exception=True);return s.validated_data
@transaction.atomic
def save(user,service,data,record=None):
    require(user,service.pk,EDIT)
    if record:record=record_for(user,record.pk,EDIT,True)
    if data.pop('version')!=(record.etag if record else 0):raise Conflict()
    norm=get_object_or_404(NormativeEntry,pk=data.pop('norm'),source__batch_id__in=catalogs(service))
    control=get_object_or_404(controls(service),pk=data.pop('control'))
    question=get_object_or_404(QuestionnaireInstance.objects.select_for_update(),pk=data.pop('question'),service=service)
    owner=get_object_or_404(get_user_model(),pk=data.pop('owner'),is_active=True)
    require(owner,service.pk,CHECK)
    doc_ids=set(data.pop('evidence'));docs=list(EvidenceDocument.objects.filter(pk__in=doc_ids,answer__instance=question))
    if len(docs)!=len(doc_ids):raise serializers.ValidationError('Evidencia ajena al servicio o pregunta.')
    answer=Answer.objects.filter(instance=question).first();answer_revision=answer.revisions.filter(version=answer.version).first() if answer else None
    if any(doc.revision_id!=(answer_revision.pk if answer_revision else None) for doc in docs):raise serializers.ValidationError('Adjunte evidencia de la versión actual de respuesta.')
    process,_=ComplianceProcess.objects.get_or_create(service=service,name=data.pop('process_name'))
    if not record:record=ComplianceRecord.objects.create(service=service,created_by=user)
    record.version+=1;record.etag+=1;record.save(update_fields=['version','etag'])
    rev=ComplianceRevision.objects.create(record=record,version=record.version,author=user,norm=norm,control=control,process=process,question=question,answer_revision=answer_revision,owner=owner,**data);rev.evidence.set(docs)
    AuditEvent.objects.create(actor=user,service=service,action='compliance.saved',object_id=str(rev.pk))
    return record
class Private(APIView):
    def finalize_response(self,request,response,*args,**kwargs):
        response=super().finalize_response(request,response,*args,**kwargs);response['Cache-Control']='private, no-store';return response
class ComplianceOptions(Private):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,service):
        service=scoped(request.user,service)
        today=timezone.localdate()
        users=get_user_model().objects.filter(is_active=True,roleassignment__service=service,roleassignment__role__in=CHECK,roleassignment__starts__lte=today,roleassignment__ends__gte=today,roleassignment__revoked_at__isnull=True).distinct()
        return Response({'can_edit':service.pk in scopes(request.user,EDIT),'can_check':service.pk in scopes(request.user,CHECK),'can_review':service.pk in scopes(request.user,APPROVE),'norms':list(NormativeEntry.objects.filter(source__batch_id__in=catalogs(service)).values('id','code','title','subject','scope_text','links','source__locator','source__batch__digest')),'controls':list(controls(service).values('id','text','locator')),'questions':[{'id':q.pk,'text':q.question_version.source.text} for q in QuestionnaireInstance.objects.filter(service=service).select_related('question_version__source')],'owners':list(users.values('id','username'))})
class ComplianceList(Private):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,service):
        scoped(request.user,service)
        page=serializers.IntegerField(min_value=1).run_validation(request.query_params.get('page',1))
        query=ComplianceRecord.objects.filter(service_id=service).order_by('id')
        return Response({'count':query.count(),'page':page,'has_next':query.count()>page*25,'results':[snapshot(r) for r in query[(page-1)*25:page*25]]})
    @extend_schema(request=ComplianceInput,responses=OpenApiTypes.OBJECT)
    def post(self,request,service):return Response(snapshot(save(request.user,scoped(request.user,service,EDIT),validated(ComplianceInput,request))),status=201)
class ComplianceDetail(Private):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,pk):
        record=record_for(request.user,pk)
        data=snapshot(record);data['history']=[{'revision':revision_data(r),'reviews':list(r.reviews.values('decision','rationale','reviewer_id','reviewer__username','created_at')),'tests':list(r.checks.values('result','procedure','expected','observed','author_id','author__username','created_at'))} for r in record.revisions.order_by('-version')]
        return Response(data)
    @extend_schema(request=ComplianceInput,responses=OpenApiTypes.OBJECT)
    def post(self,request,pk):
        record=record_for(request.user,pk,EDIT)
        return Response(snapshot(save(request.user,record.service,validated(ComplianceInput,request),record)))
class ComplianceCheck(Private):
    @extend_schema(request=ComplianceCheckInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,pk):
        record=record_for(request.user,pk,CHECK,True);data=validated(ComplianceCheckInput,request)
        if data.pop('version')!=record.etag:raise Conflict()
        check=ComplianceTest.objects.create(revision=current(record),author=request.user,**data)
        record.etag+=1;record.save(update_fields=['etag'])
        AuditEvent.objects.create(actor=request.user,service=record.service,action='compliance.test_recorded',object_id=str(check.pk))
        return Response(snapshot(record))
class ComplianceApprove(Private):
    @extend_schema(request=ComplianceReviewInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,pk):
        record=record_for(request.user,pk,APPROVE,True);data=validated(ComplianceReviewInput,request)
        if data.pop('version')!=record.etag:raise Conflict()
        rev=current(record);test=rev.checks.order_by('-id').first()
        if request.user.pk==rev.author_id or (test and request.user.pk==test.author_id):raise serializers.ValidationError('La revisión requiere otra persona distinta de autor y ejecutor de la prueba.')
        if data['decision']=='approved':
            errors=issues(rev)
            if rev.applicability=='applies' and (not test or test.result!='passed'):errors.append('Falta prueba satisfactoria de esta versión.')
            if errors:raise serializers.ValidationError(errors)
        review=ComplianceReview.objects.create(revision=rev,test=test,reviewer=request.user,**data)
        record.etag+=1;record.save(update_fields=['etag'])
        AuditEvent.objects.create(actor=request.user,service=record.service,action='compliance.reviewed',object_id=str(review.pk))
        return Response(snapshot(record))

class ComplianceExport(Private):
    renderer_classes=[JSONRenderer]
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,service):
        service=scoped(request.user,service)
        rows=ComplianceRecord.objects.filter(service=service).order_by('id')
        if rows.count()>1000:raise serializers.ValidationError('La exportación supera mil registros; solicite un paquete acotado.')
        data={'schema_version':'salud-compliance-1','created_at':timezone.now(),'author':request.user.username,'service':{'id':service.pk,'name':service.name,'site':service.site_id},'notice':'Revisión de registros; no certificación jurídica ni clínica.','records':[snapshot(r) for r in rows]}
        AuditEvent.objects.create(actor=request.user,service=service,action='compliance.exported',object_id=str(service.pk))
        response=Response(data);response['Content-Disposition']=f'attachment; filename="matriz-servicio-{service.pk}.json"';return response
