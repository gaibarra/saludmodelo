"""Periodic local drafts. No automatic approvals or external deliveries."""
import json
import uuid
from datetime import date,timedelta
from django.db import transaction
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from .access import READ,require,scopes
from .governance import require_manage,can_manage,record
from .models import Service,ReportSchedule,ScheduledReportRun,SavedReport,AuditEvent
from .capacity import Private
from .admin_serializers import StrictSerializer
from .reports import snapshot,ZONE
from .saved_reports import digest
from .workflow import Conflict

def first_period(now):
    monday=now.astimezone(ZONE).date()
    monday-=timedelta(days=monday.weekday())
    return max(date(2026,10,5),monday)

def authorize(user,service):
    if not get_user_model().objects.filter(pk=user.pk,is_active=True).exists():raise PermissionDenied('Cuenta no activa.')
    require(user,service.pk,READ);require_manage(user,service)

def serialize(schedule):
    if not schedule:return {'version':0,'enabled':False,'first_period':None,'authorized_by_id':None,'rationale':'','last_checked':None,'last_status':'not_configured','runs':[]}
    return {**{k:getattr(schedule,k) for k in ['version','enabled','first_period','authorized_by_id','rationale','last_checked','last_status']},'runs':list(schedule.runs.order_by('-period').values('period','report_id','schedule_version','generation_mode','created_at')[:20])}

class ScheduleInput(StrictSerializer):
    version=serializers.IntegerField(min_value=0)
    enabled=serializers.BooleanField()
    rationale=serializers.CharField(max_length=3000)

class ReportScheduleView(Private):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,service):
        svc=get_object_or_404(Service,pk=service,pk__in=scopes(request.user,READ))
        return Response({'can_manage':can_manage(request.user,svc),'timezone':str(ZONE),**serialize(ReportSchedule.objects.filter(service=svc).first())})
    @extend_schema(request=ScheduleInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,service):
        s=ScheduleInput(data=request.data);s.is_valid(raise_exception=True);data=s.validated_data
        svc=get_object_or_404(Service.objects.select_for_update(),pk=service,pk__in=scopes(request.user,READ))
        authorize(request.user,svc)
        schedule=ReportSchedule.objects.filter(service=svc).first()
        version=schedule.version if schedule else 0
        if data['version']!=version:
            if schedule and data['version']+1==version and schedule.authorized_by_id==request.user.pk and schedule.enabled==data['enabled'] and schedule.rationale==data['rationale']:return Response(serialize(schedule))
            raise Conflict()
        if schedule:
            if data['enabled'] and not schedule.enabled:schedule.first_period=first_period(timezone.now())
            schedule.authorized_by=request.user;schedule.enabled=data['enabled'];schedule.rationale=data['rationale'];schedule.version+=1;schedule.last_status='configuration_changed';schedule.save()
        else:
            schedule=ReportSchedule.objects.create(service=svc,authorized_by=request.user,enabled=data['enabled'],rationale=data['rationale'],first_period=first_period(timezone.now()))
        record(request.user,svc.site.campus.institution_id,'report.schedule_changed',schedule.pk,json.dumps({'version':schedule.version,'enabled':schedule.enabled,'first_period':str(schedule.first_period),'rationale':schedule.rationale},ensure_ascii=False),svc)
        return Response(serialize(schedule))

def run_schedule(pk,now=None):
    now=now or timezone.now()
    original=ReportSchedule.objects.select_related('service','authorized_by').get(pk=pk)
    if not original.enabled:return 'disabled'
    period=now.astimezone(ZONE).date();period-=timedelta(days=period.weekday()+7)
    status='waiting'
    try:
        authorize(original.authorized_by,original.service)
        if period<original.first_period:status='waiting'
        elif ScheduledReportRun.objects.filter(schedule=original,period=period).exists():status='already_generated'
        else:
            # Same consistent read-only snapshot as manual reports; no enclosing write transaction.
            content=json.loads(JSONRenderer().render(snapshot(original.authorized_by,original.service_id,period,now)))
            with transaction.atomic():
                Service.objects.select_for_update().get(pk=original.service_id)
                current=ReportSchedule.objects.select_for_update().get(pk=pk)
                if not current.enabled or current.version!=original.version:return 'configuration_changed'
                authorize(current.authorized_by,current.service)
                if ScheduledReportRun.objects.filter(schedule=current,period=period).exists():status='already_generated'
                else:
                    report=SavedReport.objects.create(service=current.service,created_by=current.authorized_by,client_key=uuid.uuid4(),start=period,content=content,content_hash=digest(content))
                    ScheduledReportRun.objects.create(schedule=current,period=period,schedule_version=current.version,report=report)
                    AuditEvent.objects.create(actor=current.authorized_by,service=current.service,action='report.scheduled_draft',object_id=str(report.pk))
                    status='generated'
    except PermissionDenied:status='authorization_required'
    except Exception:
        ReportSchedule.objects.filter(pk=pk,version=original.version).update(last_checked=now,last_status='failed')
        raise
    ReportSchedule.objects.filter(pk=pk,version=original.version).update(last_checked=now,last_status=status)
    return status


class BackfillInput(StrictSerializer):
    version=serializers.IntegerField(min_value=1)
    period=serializers.DateField()
    rationale=serializers.CharField(max_length=3000)
    def validate_period(self,value):
        today=timezone.now().astimezone(ZONE).date()
        if value<date(2026,10,5) or value.weekday()!=0 or value>today-timedelta(days=7):
            raise serializers.ValidationError('Seleccione un lunes desde el 5 de octubre de 2026 cuya semana ya haya concluido.')
        return value

class ReportBackfillView(Private):
    @extend_schema(request=BackfillInput,responses=OpenApiTypes.OBJECT)
    def post(self,request,service):
        s=BackfillInput(data=request.data);s.is_valid(raise_exception=True);data=s.validated_data
        svc=get_object_or_404(Service,pk=service,pk__in=scopes(request.user,READ))
        authorize(request.user,svc)
        schedule=get_object_or_404(ReportSchedule,service=svc)
        if schedule.version!=data['version']:raise Conflict()
        existing=ScheduledReportRun.objects.filter(schedule=schedule,period=data['period']).first()
        if existing:return Response({'report_id':existing.report_id,'created':False})
        now=timezone.now()
        content=json.loads(JSONRenderer().render(snapshot(request.user,service,data['period'],now)))
        with transaction.atomic():
            Service.objects.select_for_update().get(pk=service)
            current=ReportSchedule.objects.select_for_update().get(pk=schedule.pk)
            authorize(request.user,svc)
            if current.version!=data['version']:raise Conflict()
            existing=ScheduledReportRun.objects.filter(schedule=current,period=data['period']).first()
            if existing:return Response({'report_id':existing.report_id,'created':False})
            report=SavedReport.objects.create(service=svc,created_by=request.user,client_key=uuid.uuid4(),start=data['period'],content=content,content_hash=digest(content))
            ScheduledReportRun.objects.create(schedule=current,period=data['period'],schedule_version=current.version,report=report,generation_mode='backfill',rationale=data['rationale'])
            record(request.user,svc.site.campus.institution_id,'report.week_recovered',report.pk,json.dumps({'schedule':current.pk,'version':current.version,'period':str(data['period']),'rationale':data['rationale']},ensure_ascii=False),svc)
            AuditEvent.objects.create(actor=request.user,service=svc,action='report.backfill_draft',object_id=str(report.pk))
        return Response({'report_id':report.pk,'created':True},status=201)


class ReportScheduleHistory(Private):
    from .report_pagination import ReportHistoryPageInput
    @extend_schema(parameters=[ReportHistoryPageInput],responses=OpenApiTypes.OBJECT)
    def get(self,request,service):
        from .report_pagination import ReportHistoryPageInput,parameters,page
        from .saved_reports import serialize as report_data
        svc=get_object_or_404(Service,pk=service,pk__in=scopes(request.user,READ))
        params=parameters(ReportHistoryPageInput,request)
        rows,next_before=page(ScheduledReportRun.objects.filter(schedule__service=svc).select_related('report'),params)
        return Response({'results':[{'id':r.pk,'period':r.period,'schedule_version':r.schedule_version,'generation_mode':r.generation_mode,'rationale':r.rationale,'created_at':r.created_at,'report':report_data(r.report)} for r in rows],'next_before':next_before})
