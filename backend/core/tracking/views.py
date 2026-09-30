from core.time_accounting import total,effective
from core.coverage import coverages,coverage_event_valid
from datetime import date,timedelta
from pathlib import Path
import json
from django.db import transaction,models
from django.db.models import Sum,Exists,OuterRef
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from core.models import *
from core.access import scopes,READ
from core.governance import managed_services,managed_institutions,require_institution
from core.admin_serializers import StrictSerializer
from core.workflow import Conflict
from . import workflow as flow
from .administrative_time import authorized as administrative_authorized

class ReservationInput(StrictSerializer):
    person=serializers.IntegerField(min_value=1)
    day=serializers.DateField()
    minutes=serializers.IntegerField(min_value=1,max_value=1440)

class TaskFields(StrictSerializer):
    reservation_plan=ReservationInput(many=True,required=False,default=list)
    budget_bucket=serializers.ChoiceField(choices=['base','reserve'],default='base')
    title=serializers.CharField(max_length=250)
    owner=serializers.IntegerField(min_value=1)
    substitute=serializers.IntegerField(min_value=1,allow_null=True)
    coordinator=serializers.IntegerField(min_value=1,allow_null=True)
    starts=serializers.DateField()
    due=serializers.DateField()
    priority=serializers.ChoiceField(choices=['low','normal','high','critical'])
    estimated_minutes=serializers.IntegerField(min_value=0,max_value=1000000)
    acceptance_criteria=serializers.CharField(max_length=5000)
    predecessors=serializers.ListField(child=serializers.IntegerField(min_value=1),max_length=50)
class ChangeInput(TaskFields):
    version=serializers.IntegerField(min_value=0)
    rationale=serializers.CharField(max_length=5000)
    cancel=serializers.BooleanField(default=False)
class BaselineDecisionInput(StrictSerializer):
    approve=serializers.BooleanField()
    rationale=serializers.CharField(max_length=5000)
class TaskStateInput(StrictSerializer):
    version=serializers.IntegerField(min_value=0)
    target=serializers.ChoiceField(choices=['in_progress','blocked','submitted','accepted','returned'])
    note=serializers.CharField(max_length=5000)
class TimeInput(StrictSerializer):
    day=serializers.DateField()
    minutes=serializers.IntegerField(min_value=1,max_value=1440)
    note=serializers.CharField(max_length=2000)
    client_key=serializers.UUIDField()
class CalendarInput(StrictSerializer):
    version=serializers.IntegerField(min_value=0)
    weekdays=serializers.ListField(child=serializers.IntegerField(min_value=0,max_value=6),min_length=1,max_length=7)
    holidays=serializers.ListField(child=serializers.DateField(),max_length=1000)
    rationale=serializers.CharField(max_length=5000)

def data(cls,request):
    s=cls(data=request.data);s.is_valid(raise_exception=True);return s.validated_data
def service_for(user,pk):
    # An institution mandate configures calendars; task data still requires a service assignment.
    return get_object_or_404(Service.objects.select_related('site__campus'),pk=pk,pk__in=scopes(user))
def task_for(user,pk):return get_object_or_404(Task,pk=pk,service_id__in=scopes(user))
def summary(task):
    return {'id':task.pk,'service':task.service_id,'etag':task.etag,'committed':task.committed,'state':task.state,'blocked_since':task.blocked_since,'owner_name':task.owner.username,'active_substitutions':list(coverages(task.service_id,task.owner_id).values('id','user_id','user__username','starts','ends')),'actual_minutes':total(task.time_entries.all()),**flow.fields(task)}
def detail(task,user=None):
    task=Task.objects.select_related('owner','service__site__campus').get(pk=task.pk)
    return {**summary(task),'changes':list(task.baseline_changes.order_by('-id').values('id','expected_etag','requested_by__username','proposal','previous','rationale','state','reviewed_by__username','review_reason','created_at','reviewed_at')[:100]),'events':list(task.events.order_by('-id').values('actor__username','kind','note','snapshot','created_at')[:100]),'time_entries':[{**row,'can_correct':bool(user and row['actor_id']==user.pk and task.service_id in scopes(user,flow.WORK)),'can_request_correction':bool(user and row['actor_id']!=user.pk and administrative_authorized(user,task.service_id)),'corrections':list(TimeCorrection.objects.filter(entry_id=row['id']).order_by('-version').values('version','minutes','rationale','actor__username','created_at')[:100])} for row in effective(task.time_entries.all()).order_by('-id').values('id','actor_id','actor__username','day','minutes','note','effective_minutes','correction_version')[:100]]}
def metric(n,d):return {'numerator':n,'denominator':d,'pending':d-n,'label':'Sin alcance definido' if not d else f'{n} de {d}'}

def forecast(tasks,plan,now):
    """Finish-to-start proposals only; blocked chains keep unknown dates."""
    days=set(plan.weekdays) if plan and plan.confirmed_by_id else set(range(5));holidays=set(plan.holidays) if plan and plan.confirmed_by_id else set()
    def work(day):return day.weekday() in days and str(day) not in holidays
    def advance(day):
        for _ in range(3661):
            if work(day):return day
            day+=timedelta(days=1)
        raise serializers.ValidationError('Calendario fuera de límite.')
    by_id={t.pk:t for t in tasks};remaining=set(by_id);result={}
    deps={t.pk:list(t.dependencies.values_list('predecessor_id',flat=True)) for t in tasks}
    while remaining:
        ready=[pk for pk in remaining if all(p not in remaining for p in deps[pk])]
        if not ready:raise serializers.ValidationError('Dependencias inconsistentes; revise el grafo.')
        for pk in ready:
            task=by_id[pk];parents=[]
            for parent_id in deps[pk]:
                if parent_id in result:parents.append(result[parent_id])
                else:
                    external=Task.objects.filter(pk=parent_id,state='accepted').first()
                    parents.append({'due':external.due} if external else None)
            if task.state in ['blocked','cancelled'] or any(p is None or p['due'] is None for p in parents):result[pk]={'starts':None,'due':None,'blocked':True}
            else:
                start=max([task.starts]+([now] if task.state!='accepted' else [])+[p['due']+timedelta(days=1) for p in parents])
                start=advance(start);duration=max(1,sum(work(task.starts+timedelta(days=i)) for i in range((task.due-task.starts).days+1)))
                end=start
                for _ in range(duration-1):end=advance(end+timedelta(days=1))
                result[pk]={'starts':start,'due':end,'blocked':False}
            remaining.remove(pk)
    return [{'task':pk,**value,'proposed_only':True} for pk,value in result.items()]

class Private(APIView):
    def finalize_response(self,request,response,*args,**kwargs):
        response=super().finalize_response(request,response,*args,**kwargs);response['Cache-Control']='private, no-store';return response
class Board(Private):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,service):
        service=service_for(request.user,service)
        tasks=list(Task.objects.filter(service=service).select_related('owner').prefetch_related('dependencies').order_by('due','id'))
        if len(tasks)>1000:raise serializers.ValidationError('El tablero supera mil tareas; requiere paginación ampliada antes de incorporar más.')
        plan=WorkPlan.objects.filter(institution=service.site.campus.institution).first();now=flow.today(service)
        users=RoleAssignment.objects.filter(service=service,starts__lte=timezone.localdate(),ends__gte=timezone.localdate(),revoked_at__isnull=True,user__is_active=True,role__in=flow.WORK|{'director'}).values('user_id','user__username','role')
        q=QuestionnaireInstance.objects.filter(service=service,service__confirmed=True)
        sufficient_revision=AnswerRevision.objects.filter(answer_id=OuterRef('pk'),version=OuterRef('version'),knowledge='known').exclude(content__regex=r'^\s*$')
        sufficient=Answer.objects.filter(instance__in=q,state__in=['submitted','validated']).annotate(sufficient=Exists(sufficient_revision)).filter(sufficient=True).count()
        committed=[t for t in tasks if t.committed];active=[t for t in tasks if t.state not in ['accepted','cancelled']]
        def ids(items):return [t.pk for t in items]
        return Response({'updated_at':timezone.now(),'today':now,'timezone':service.site.timezone,'can_edit':service.pk in scopes(request.user,flow.EDIT),'can_work':service.pk in scopes(request.user,flow.WORK|{'director'}),'can_review_baseline':managed_services(request.user).filter(pk=service.pk).exists(),'can_calendar':service.site.campus.institution_id in managed_institutions(request.user),'people':list(users),'tasks':[summary(t) for t in tasks],'forecast':forecast(tasks,plan,now),'calendar':{'etag':plan.etag if plan else 0,'confirmed':bool(plan and plan.confirmed_by_id),'weekdays':plan.weekdays if plan else list(range(5)),'holidays':plan.holidays if plan else [],'rationale':plan.rationale if plan else ''},'capacity_reference':{'base_hours':295,'reserve_hours':59,'total_hours':354,'status':'provisional_institutional_reference','scope_note':'No multiplique esta capacidad por servicio; horas reales aquí sólo del servicio visible.','reserve_used':None},'metrics':{'capture':metric(sufficient,q.count()),'validated':metric(Answer.objects.filter(instance__in=q,state='validated').count(),q.count()),'accepted':metric(sum(t.state=='accepted' for t in committed),len(committed)),'cancelled_committed':sum(t.state=='cancelled' for t in committed),'actual_minutes':sum(total(t.time_entries.all()) for t in tasks),'estimated_minutes':sum(t.estimated_minutes for t in committed),'uncommitted':len(tasks)-len(committed),'overdue':ids(t for t in active if t.due<now),'due_soon':ids(t for t in active if now<=t.due<=now+timedelta(days=7)),'blocked':ids(t for t in active if t.state=='blocked'),'critical':ids(t for t in active if t.priority=='critical'),'load':[{'owner':uid,'name':name,'tasks':ids(t for t in active if t.owner_id==uid),'estimated_minutes':sum(t.estimated_minutes for t in active if t.owner_id==uid)} for uid,name in sorted({(t.owner_id,t.owner.username) for t in tasks})]},'unavailable_metrics':['Aceptación integral de procesos y servicios: faltan criterios de salida aprobados.','Consumo de reserva: falta asignación institucional de capacidad.'],'notifications':[{'id':n.pk,'event__task_id':n.event.task_id,'event__key':n.event.key,'created_at':n.created_at,'coverage_id':n.event.coverage_id} for n in Notification.objects.filter(recipient=request.user,event__task__service=service).select_related('event__task').order_by('-id')[:100] if coverage_event_valid(n.event)]})
    @extend_schema(request=TaskFields,responses=OpenApiTypes.OBJECT)
    def post(self,request,service):return Response(detail(flow.create(request.user,service_for(request.user,service),data(TaskFields,request))),status=201)
class TaskDetail(Private):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,pk):return Response(detail(task_for(request.user,pk),request.user))
class TaskChange(Private):
    @extend_schema(request=ChangeInput,responses=OpenApiTypes.OBJECT)
    def post(self,request,pk):
        task=task_for(request.user,pk);values=data(ChangeInput,request);version=values.pop('version');reason=values.pop('rationale');cancel=values.pop('cancel')
        flow.propose(request.user,task.pk,version,values,reason,cancel);return Response(detail(task))
class BaselineDecision(Private):
    @extend_schema(request=BaselineDecisionInput,responses=OpenApiTypes.OBJECT)
    def post(self,request,pk):
        change=get_object_or_404(BaselineChange,pk=pk,task__service__in=managed_services(request.user));values=data(BaselineDecisionInput,request)
        return Response(detail(flow.decide(request.user,change.pk,**values)))
class TaskState(Private):
    @extend_schema(request=TaskStateInput,responses=OpenApiTypes.OBJECT)
    def post(self,request,pk):return Response(detail(flow.transition(request.user,task_for(request.user,pk).pk,**data(TaskStateInput,request))))
class TaskTime(Private):
    @extend_schema(request=TimeInput,responses=OpenApiTypes.OBJECT)
    def post(self,request,pk):
        task=task_for(request.user,pk);flow.time_entry(request.user,task,data(TimeInput,request));return Response(detail(task))
class Calendar(Private):
    @extend_schema(request=CalendarInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,service):
        service=get_object_or_404(Service,pk=service);institution=service.site.campus.institution;require_institution(request.user,institution.pk)
        Institution.objects.select_for_update().get(pk=institution.pk)
        values=data(CalendarInput,request);plan,_=WorkPlan.objects.get_or_create(institution=institution)
        if values['version']!=plan.etag:raise Conflict()
        plan.weekdays=sorted(set(values['weekdays']));plan.holidays=sorted({str(d) for d in values['holidays']});plan.rationale=values['rationale'];plan.etag+=1;plan.confirmed_by=request.user;plan.confirmed_at=timezone.now();plan.save()
        WorkCalendarRevision.objects.create(plan=plan,version=plan.etag,actor=request.user,weekdays=plan.weekdays,holidays=plan.holidays,rationale=plan.rationale)
        return Response({'etag':plan.etag,'confirmed':True})
class SourceCalendar(Private):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,service):
        service=service_for(request.user,service)
        source=json.loads((Path(__file__).resolve().parents[3]/'imports/work-calendar-reference.json').read_text())
        if not CatalogAccess.objects.filter(institution=service.site.campus.institution,batch__digest=source['source_sha256']).exists():raise serializers.ValidationError('El catálogo fuente no está autorizado para esta institución.')
        return Response(source)

class TimeCorrectionInput(StrictSerializer):
    version=serializers.IntegerField(min_value=0)
    minutes=serializers.IntegerField(min_value=0,max_value=1440)
    rationale=serializers.CharField(max_length=2000)

class TaskTimeCorrection(Private):
    @extend_schema(request=TimeCorrectionInput,responses=OpenApiTypes.OBJECT)
    def post(self,request,pk):
        return Response(detail(flow.correct_time(request.user,pk,**data(TimeCorrectionInput,request)),request.user))

class BaselinePreview(Private):
    @extend_schema(request=None,responses=OpenApiTypes.OBJECT)
    def post(self,request,pk):
        from rest_framework.exceptions import APIException
        get_object_or_404(BaselineChange,pk=pk,task__service__in=managed_services(request.user))
        # Use the approval path under identical locks, then roll back every write.
        with transaction.atomic():
            try:
                task=flow.decide(request.user,pk,True,'Simulación de aprobación; no persistida.')
                result={'can_approve':True,'task':task.pk,'message':'La propuesta puede aprobarse con los datos actuales. Se volverá a validar al aprobar.'}
            except APIException as error:
                if error.status_code in [401,403,404]:raise
                result={'can_approve':False,'message':str(error.detail)}
            transaction.set_rollback(True)
        return Response(result)

class DependencyOptions(Private):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,service):
        service=service_for(request.user,service)
        rows=list(Task.objects.filter(service_id__in=scopes(request.user,READ),service__site__campus__institution_id=service.site.campus.institution_id).exclude(state='cancelled').order_by('id').values('id','title','service_id','service__name','due')[:1001])
        if len(rows)>1000:raise serializers.ValidationError('Más de mil opciones de dependencia; acote el catálogo.')
        return Response(rows)

class HistoryInput(StrictSerializer):
    kind=serializers.ChoiceField(choices=['events','changes','time','corrections'])
    before=serializers.IntegerField(min_value=1,max_value=9223372036854775807,required=False)

class TaskHistory(Private):
    @extend_schema(parameters=[HistoryInput],responses=OpenApiTypes.OBJECT)
    def get(self,request,pk):
        task=task_for(request.user,pk)
        s=HistoryInput(data=request.query_params);s.is_valid(raise_exception=True);params=s.validated_data
        kind=params['kind']
        if kind=='events':query=task.events.values('id','actor__username','kind','note','snapshot','created_at')
        elif kind=='changes':query=task.baseline_changes.values('id','requested_by__username','state','rationale','proposal','previous','reviewed_by__username','review_reason','created_at')
        elif kind=='corrections':query=TimeCorrection.objects.filter(entry__task=task).values('id','entry_id','version','minutes','rationale','actor__username','created_at')
        else:query=effective(task.time_entries.all()).values('id','actor_id','actor__username','day','minutes','effective_minutes','correction_version','budget_bucket','note','created_at')
        if 'before' in params:query=query.filter(id__lt=params['before'])
        rows=list(query.order_by('-id')[:51]);next_before=rows[49]['id'] if len(rows)>50 else None;rows=rows[:50]
        if kind=='time':
            for row in rows:
                row['can_correct']=row['actor_id']==request.user.pk and task.service_id in scopes(request.user,flow.WORK)
                row['can_request_correction']=row['actor_id']!=request.user.pk and administrative_authorized(request.user,task.service_id)
        return Response({'results':rows,'next_before':next_before})

class AdministrativeTimeInput(TimeCorrectionInput):
    client_key=serializers.UUIDField()

class AdministrativeTimeRequest(Private):
    @extend_schema(request=AdministrativeTimeInput,responses=OpenApiTypes.OBJECT)
    def post(self,request,pk):
        from . import administrative_time as admin
        result=admin.propose(request.user,pk,**data(AdministrativeTimeInput,request))
        return Response(admin.serialize(result,request.user),status=201)

class AdministrativeTimeDecision(Private):
    @extend_schema(request=BaselineDecisionInput,responses=OpenApiTypes.OBJECT)
    def post(self,request,pk):
        from . import administrative_time as admin
        result=admin.decide(request.user,pk,**data(BaselineDecisionInput,request))
        return Response(admin.serialize(result,request.user))

class AdministrativeTimePageInput(StrictSerializer):
    before=serializers.IntegerField(min_value=1,max_value=9223372036854775807,required=False)

class AdministrativeTimeList(Private):
    @extend_schema(parameters=[AdministrativeTimePageInput],responses=OpenApiTypes.OBJECT)
    def get(self,request,pk):
        from . import administrative_time as admin
        task=task_for(request.user,pk)
        s=AdministrativeTimePageInput(data=request.query_params);s.is_valid(raise_exception=True)
        query=AdministrativeTimeCorrection.objects.filter(entry__task=task).select_related('entry__actor','entry__task','requested_by','reviewed_by')
        if 'before' in s.validated_data:query=query.filter(id__lt=s.validated_data['before'])
        rows=list(query.order_by('-id')[:51])
        return Response({'results':[admin.serialize(r,request.user) for r in rows[:50]],'next_before':rows[49].pk if len(rows)>50 else None})
