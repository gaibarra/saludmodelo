"""Capacity reservations validated under the institution lock at baseline approval."""
import json
from datetime import date
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from .models import Institution,PlanningPolicy,TaskReservation,Task,TimeEntry,CapacityDay,RoleAssignment,WorkPlan,GovernanceEvent
from .capacity import Private
from .admin_serializers import StrictSerializer
from .governance import require_institution
from .workflow import Conflict
from .tracking.workflow import WORK

def normalize(data):
    rows=data.get('reservation_plan',[])
    if len(rows)>500:raise serializers.ValidationError('Máximo 500 reservas por tarea.')
    seen=set();result=[]
    for row in rows:
        day=date.fromisoformat(str(row['day']));key=(row['person'],day)
        if key in seen:raise serializers.ValidationError('No repita persona y fecha en reservas.')
        seen.add(key)
        if row['person'] not in {data['owner'],data.get('substitute')} or not date.fromisoformat(str(data['starts']))<=day<=date.fromisoformat(str(data['due'])):
            raise serializers.ValidationError('Reserve sólo al responsable o suplente explícito dentro de las fechas de la tarea.')
        result.append({**row,'day':str(day)})
    if rows and sum(r['minutes'] for r in rows)!=data['estimated_minutes']:raise serializers.ValidationError('Las reservas deben sumar exactamente la estimación.')
    return result

def commit_reservations(task):
    task.reservations.all().delete()
    if task.state=='cancelled':return
    institution=task.service.site.campus.institution_id
    for row in task.reservation_plan:
        day=CapacityDay.objects.filter(institution_id=institution,person_id=row['person'],day=row['day']).first()
        TaskReservation.objects.create(task=task,person_id=row['person'],day=row['day'],minutes=row['minutes'],capacity_version=day.etag if day else 0)

def check(institution):
    policy=PlanningPolicy.objects.filter(institution_id=institution).first()
    tasks=Task.objects.filter(service__site__campus__institution_id=institution,committed=True).exclude(state='cancelled')
    issues=[]
    active=tasks.exclude(state='accepted')
    if policy and policy.enforced:
        for t in active:
            if (t.reservations.aggregate(total=Sum('minutes'))['total'] or 0)!=t.estimated_minutes:
                issues.append({'task':t.pk,'reason':'missing_reservations'})
    reservations=TaskReservation.objects.filter(task__in=tasks).select_related('task__service')
    loads={}
    calendar=WorkPlan.objects.filter(institution_id=institution,confirmed_by__isnull=False).first()
    for r in reservations:
        key=(r.person_id,r.day,r.task.service_id);loads[key]=loads.get(key,0)+r.minutes
    for (person,day,service),minutes in sorted(loads.items()):
        capacity=CapacityDay.objects.filter(institution_id=institution,person_id=person,day=day,confirmed=True).first()
        allocation=capacity.allocations.filter(service_id=service).first() if capacity else None
        valid=RoleAssignment.objects.filter(service_id=service,user_id=person,user__is_active=True,role__in=WORK,revoked_at__isnull=True,starts__lte=day,ends__gte=day).exists()
        reason=None
        if not calendar or day.weekday() not in calendar.weekdays or str(day) in calendar.holidays:reason='calendar'
        elif not valid:reason='assignment'
        elif not capacity:reason='unconfirmed_capacity'
        elif minutes>(allocation.minutes if allocation else 0):reason='over_capacity'
        if reason:issues.append({'person':person,'day':str(day),'service':service,'minutes':minutes,'reason':reason})
    budgets={}
    for bucket in ['base','reserve']:
        used=tasks.filter(budget_bucket=bucket).aggregate(total=Sum('estimated_minutes'))['total'] or 0
        limit=getattr(policy,bucket+'_minutes') if policy else None
        from .time_accounting import effective
        actual_rows=effective(TimeEntry.objects.filter(task__service__site__campus__institution_id=institution,budget_bucket=bucket)).values('task_id').annotate(total=Sum('effective_minutes'))
        spent={row['task_id']:row['total'] for row in actual_rows};actual=sum(spent.values())
        exposure=sum(max(t.estimated_minutes,spent.pop(t.pk,0)) for t in tasks.filter(budget_bucket=bucket))+sum(spent.values())
        budgets[bucket]={'actual_minutes':actual,'committed_minutes':used,'exposure_minutes':exposure,'approved_minutes':limit,'remaining_minutes':limit-exposure if limit is not None else None}
        if policy and exposure>limit:issues.append({'reason':'budget_exceeded','bucket':bucket,'minutes':exposure-limit})
    return {'enforced':bool(policy and policy.enforced),'version':policy.etag if policy else 0,'budgets':budgets,'issues':issues}

def validate_institution(institution,previous=None):
    result=check(institution)
    def signature(issue):return json.dumps({k:v for k,v in issue.items() if k!='minutes'},sort_keys=True)
    previous_issues={signature(i):i.get('minutes',0) for i in (previous or {}).get('issues',[])}
    worsened=[i for i in result['issues'] if signature(i) not in previous_issues or i.get('minutes',0)>previous_issues[signature(i)]]
    if worsened:raise serializers.ValidationError('La aprobación crea o agrava conflictos de reservas, presupuesto o capacidad. Revise el control institucional.')

class PolicyInput(StrictSerializer):
    version=serializers.IntegerField(min_value=0)
    enforced=serializers.BooleanField()
    base_minutes=serializers.IntegerField(min_value=0,max_value=100000000)
    reserve_minutes=serializers.IntegerField(min_value=0,max_value=100000000)
    rationale=serializers.CharField(max_length=3000)

class PlanningControl(Private):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def get(self,request,institution):
        require_institution(request.user,institution)
        Institution.objects.select_for_update().get(pk=institution)
        require_institution(request.user,institution)
        return Response(check(institution))
    @extend_schema(request=PolicyInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,institution):
        require_institution(request.user,institution)
        Institution.objects.select_for_update().get(pk=institution)
        require_institution(request.user,institution)
        s=PolicyInput(data=request.data);s.is_valid(raise_exception=True);data=s.validated_data
        policy,_=PlanningPolicy.objects.get_or_create(institution_id=institution)
        if policy.etag!=data['version']:raise Conflict()
        previous={'enforced':policy.enforced,'base_minutes':policy.base_minutes,'reserve_minutes':policy.reserve_minutes}
        policy.enforced=data['enforced'];policy.base_minutes=data['base_minutes'];policy.reserve_minutes=data['reserve_minutes'];policy.etag+=1;policy.save()
        validate_institution(institution)
        GovernanceEvent.objects.create(institution_id=institution,actor=request.user,action='planning.control_changed',object_id=str(policy.pk),rationale=json.dumps({'previous':previous,'current':data,'version':policy.etag},ensure_ascii=False))
        return Response(check(institution))
