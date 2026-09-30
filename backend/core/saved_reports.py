"""Frozen weekly reports and independent review; never sends a report."""
import hashlib
import json
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from .capacity import Private
from .access import READ, require, scopes
from .admin_serializers import StrictSerializer
from .governance import require_manage
from .models import SavedReport, Service, AuditEvent, ReportDisposition, ScheduledReportRun
from .reports import snapshot, ZONE
from .tracking.workflow import WORK
from .workflow import Conflict
from .report_pagination import SavedReportPageInput,parameters,page

class SaveReportInput(StrictSerializer):
    start = serializers.DateField()
    client_key = serializers.UUIDField()
    def validate_start(self, value):
        if value > timezone.now().astimezone(ZONE).date():
            raise serializers.ValidationError('El período no puede comenzar en el futuro.')
        return value

class SavedReportReviewInput(StrictSerializer):
    approve = serializers.BooleanField()
    content_hash = serializers.CharField(min_length=64,max_length=64)
    rationale = serializers.CharField(max_length=3000)

def digest(content):
    return hashlib.sha256(json.dumps(content,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def serialize(row, full=False):
    data = {key:getattr(row,key) for key in ['id','service_id','created_by_id','start','content_hash','state','reviewed_by_id','rationale','reviewed_at','created_at']}
    generated=ScheduledReportRun.objects.filter(report=row).first()
    data['generation']=({'kind':generated.generation_mode,'rationale':generated.rationale,'schedule_id':generated.schedule_id,'schedule_version':generated.schedule_version,'period':generated.period} if generated else {'kind':'manual'})
    disposition=ReportDisposition.objects.filter(report=row).first()
    data['availability']='superseded' if disposition and disposition.replacement_id else 'withdrawn' if disposition else 'retained'
    data['disposition']=({'replacement_id':disposition.replacement_id,'actor_id':disposition.actor_id,'rationale':disposition.rationale,'created_at':disposition.created_at} if disposition else None)
    if full:
        if digest(row.content) != row.content_hash:
            raise serializers.ValidationError('La integridad del informe requiere revisión técnica.')
        data['content'] = row.content
        data['distribution']={'channel':'internal','delivered':row.deliveries.count(),'acknowledged':row.deliveries.filter(acknowledged_at__isnull=False).count()}
    return data

def existing(user,service,data):
    row=SavedReport.objects.filter(service_id=service,created_by=user,client_key=data['client_key']).first()
    if row and row.start != data['start']:
        raise serializers.ValidationError('Clave usada para otro período.')
    return row

class SavedReportList(Private):
    @extend_schema(parameters=[SavedReportPageInput],responses=OpenApiTypes.OBJECT)
    def get(self,request,service):
        require(request.user,service,READ)
        params=parameters(SavedReportPageInput,request)
        query=SavedReport.objects.filter(service_id=service)
        if 'start' in params:query=query.filter(start=params['start'])
        if 'state' in params:query=query.filter(state=params['state'])
        if 'exclude' in params:query=query.exclude(pk=params['exclude'])
        if params['retained_only']:query=query.exclude(pk__in=ReportDisposition.objects.values('report_id'))
        rows,next_before=page(query,params)
        return Response({'results':[serialize(r) for r in rows],'next_before':next_before})

    @extend_schema(request=SaveReportInput,responses=OpenApiTypes.OBJECT)
    def post(self,request,service):
        s=SaveReportInput(data=request.data);s.is_valid(raise_exception=True);data=s.validated_data
        require(request.user,service,WORK|{'director'})
        row=existing(request.user,service,data)
        if row:return Response(serialize(row,True))
        # Snapshot owns its read-only transaction; saving happens afterwards.
        content=json.loads(JSONRenderer().render(snapshot(request.user,service,data['start'],timezone.now())))
        with transaction.atomic():
            Service.objects.select_for_update().get(pk=service)
            require(request.user,service,WORK|{'director'})
            row=existing(request.user,service,data)
            if row:return Response(serialize(row,True))
            row=SavedReport.objects.create(service_id=service,created_by=request.user,client_key=data['client_key'],start=data['start'],content=content,content_hash=digest(content))
            AuditEvent.objects.create(actor=request.user,service_id=service,action='report.saved',object_id=str(row.pk))
        return Response(serialize(row,True),status=201)

class SavedReportDetail(Private):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,pk):
        row=get_object_or_404(SavedReport,pk=pk,service_id__in=scopes(request.user,READ))
        data=serialize(row,True)
        AuditEvent.objects.create(actor=request.user,service_id=row.service_id,action='report.saved_exported',object_id=str(row.pk))
        response=Response(data)
        response['Content-Disposition']=f'attachment; filename="salud-saved-report-{row.pk}.json"'
        return response

    @extend_schema(request=SavedReportReviewInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,pk):
        s=SavedReportReviewInput(data=request.data);s.is_valid(raise_exception=True);data=s.validated_data
        original=get_object_or_404(SavedReport,pk=pk,service_id__in=scopes(request.user,READ))
        Service.objects.select_for_update().get(pk=original.service_id)
        row=SavedReport.objects.select_for_update().get(pk=pk)
        require_manage(request.user,row.service)
        require(request.user,row.service_id,READ)
        if row.created_by_id==request.user.pk:raise serializers.ValidationError('Otra persona de Dirección debe revisar el informe.')
        serialize(row,True)
        if data['content_hash']!=row.content_hash:raise Conflict()
        if ReportDisposition.objects.filter(report=row).exists():raise Conflict()
        target='approved' if data['approve'] else 'rejected'
        if row.state!='pending':
            if row.state==target and row.reviewed_by_id==request.user.pk and row.rationale==data['rationale']:return Response(serialize(row,True))
            raise Conflict()
        row.state=target;row.reviewed_by=request.user;row.rationale=data['rationale'];row.reviewed_at=timezone.now()
        row.save(update_fields=['state','reviewed_by','rationale','reviewed_at'])
        AuditEvent.objects.create(actor=request.user,service_id=row.service_id,action='report.'+target,object_id=str(row.pk))
        return Response(serialize(row,True))


class ReportDispositionInput(StrictSerializer):
    content_hash = serializers.CharField(min_length=64,max_length=64)
    expected_state = serializers.ChoiceField(choices=['pending','approved','rejected'])
    replacement = serializers.IntegerField(min_value=1,allow_null=True)
    replacement_hash = serializers.CharField(min_length=64,max_length=64,allow_null=True)
    rationale = serializers.CharField(max_length=3000)
    def validate(self,data):
        if (data['replacement'] is None)!=(data['replacement_hash'] is None):
            raise serializers.ValidationError('Indique versión sustituta y su huella juntas.')
        return data

class ReportDispositionView(Private):
    @extend_schema(request=ReportDispositionInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,pk):
        s=ReportDispositionInput(data=request.data);s.is_valid(raise_exception=True);data=s.validated_data
        original=get_object_or_404(SavedReport,pk=pk,service_id__in=scopes(request.user,READ))
        Service.objects.select_for_update().get(pk=original.service_id)
        row=SavedReport.objects.select_for_update().get(pk=pk)
        require(request.user,row.service_id,READ)
        # Authors may withdraw only their own still-pending draft; all other cases need Direction.
        if not (row.created_by_id==request.user.pk and row.state=='pending' and data['replacement'] is None):
            require_manage(request.user,row.service)
        serialize(row,True)
        if row.content_hash!=data['content_hash'] or row.state!=data['expected_state']:raise Conflict()
        prior=ReportDisposition.objects.filter(report=row).first()
        if prior:
            if prior.actor_id==request.user.pk and prior.replacement_id==data['replacement'] and prior.rationale==data['rationale']:
                if prior.replacement_id and SavedReport.objects.get(pk=prior.replacement_id).content_hash!=data['replacement_hash']:raise Conflict()
                return Response(serialize(row,True))
            raise Conflict()
        replacement=None
        if data['replacement'] is not None:
            replacement=get_object_or_404(SavedReport,pk=data['replacement'],service_id=row.service_id)
            if replacement.pk==row.pk or replacement.start!=row.start or replacement.state!='approved' or ReportDisposition.objects.filter(report=replacement).exists():
                raise serializers.ValidationError('El sustituto debe ser otro informe aprobado, no retirado, del mismo servicio y período.')
            serialize(replacement,True)
            if replacement.content_hash!=data['replacement_hash']:raise Conflict()
        ReportDisposition.objects.create(report=row,replacement=replacement,actor=request.user,rationale=data['rationale'],expected_state=data['expected_state'])
        AuditEvent.objects.create(actor=request.user,service_id=row.service_id,action='report.superseded' if replacement else 'report.withdrawn',object_id=str(row.pk))
        return Response(serialize(row,True))
