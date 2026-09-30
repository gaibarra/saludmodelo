"""Read-only comparison of baseline task estimates and approved service capacity."""
from datetime import date,timedelta
from django.db import transaction,connection
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from .capacity import Private
from .tracking.workflow import WORK
from .access import scopes,READ
from .models import Service,Task,CapacityDay,WorkPlan,RoleAssignment
from .admin_serializers import StrictSerializer

class PlanningPeriod(StrictSerializer):
    start=serializers.DateField()
    def validate_start(self,value):
        if not date(2026,10,1)<=value<=date(9999,12,24):raise serializers.ValidationError('Fecha fuera del intervalo de planificación.')
        return value

class TaskCapacity(Private):
    @extend_schema(parameters=[PlanningPeriod],responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def get(self,request,service):
        # All dependent reads observe the same committed snapshot.
        with connection.cursor() as cursor:
            cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
            cursor.execute("SET LOCAL statement_timeout = '5000ms'")
        service=get_object_or_404(Service.objects.select_related('site__campus'),pk=service,pk__in=scopes(request.user,READ))
        p=PlanningPeriod(data=request.query_params);p.is_valid(raise_exception=True)
        start=p.validated_data['start'];end=start+timedelta(days=7)
        institution=service.site.campus.institution_id
        plan=WorkPlan.objects.filter(institution_id=institution).first()
        result={'start':start,'end_exclusive':end,'observed_at':timezone.now(),'calendar_confirmed':bool(plan and plan.confirmed_by_id),'calendar_version':plan.etag if plan else 0,'rows':[],'issues':[],'method':'baseline_estimate_even_workdays','proposed_only':True}
        if not result['calendar_confirmed']:return Response(result)
        tasks=list(Task.objects.filter(service=service,committed=True,starts__lt=end,due__gte=start).exclude(state__in=['accepted','cancelled']).select_related('owner').order_by('id')[:1001])
        if len(tasks)>1000:raise serializers.ValidationError('Más de mil tareas; acote el plan antes de consultar capacidad.')
        weekdays=set(plan.weekdays);holidays=set(plan.holidays);loads={}
        for task in tasks:
            span=(task.due-task.starts).days+1
            if span>3660:raise serializers.ValidationError('Una tarea supera diez años; revise su intervalo.')
            days=[task.starts+timedelta(days=i) for i in range(span) if (task.starts+timedelta(days=i)).weekday() in weekdays and str(task.starts+timedelta(days=i)) not in holidays]
            if not days or not task.estimated_minutes:
                result['issues'].append({'task_id':task.pk,'title':task.title,'reason':'no_workdays' if not days else 'missing_estimate'});continue
            base,remainder=divmod(task.estimated_minutes,len(days))
            for index,day in enumerate(days):
                if not start<=day<end:continue
                minutes=base+(index<remainder)
                if not minutes:continue
                row=loads.setdefault((task.owner_id,day),{'person_id':task.owner_id,'name':task.owner.username,'day':day,'planned_minutes':0,'tasks':[]})
                row['planned_minutes']+=minutes;row['tasks'].append({'id':task.pk,'title':task.title,'version':task.etag,'minutes':minutes})
        capacities={(d.person_id,d.day):d for d in CapacityDay.objects.filter(institution_id=institution,person_id__in={key[0] for key in loads},day__gte=start,day__lt=end).prefetch_related('allocations')}
        grants=list(RoleAssignment.objects.filter(service=service,user_id__in={key[0] for key in loads},user__is_active=True,role__in=WORK|{'director'},revoked_at__isnull=True,starts__lt=end,ends__gte=start).values('user_id','starts','ends'))
        valid_days={(g['user_id'],start+timedelta(days=i)) for g in grants for i in range(7) if g['starts']<=start+timedelta(days=i)<=g['ends']}
        for key,row in sorted(loads.items(),key=lambda item:(item[0][1],item[0][0])):
            day=capacities.get(key);valid=key in valid_days
            confirmed=bool(day and day.confirmed)
            allocated=next((a.minutes for a in day.allocations.all() if a.service_id==service.pk),0) if confirmed else None
            status='assignment_review' if not valid else 'unconfirmed' if not confirmed else 'overloaded' if row['planned_minutes']>allocated else 'within_capacity'
            row.update(status=status,capacity_version=day.etag if day else 0,allocated_minutes=allocated if valid else None,has_unavailability=bool(confirmed and day.unavailable_minutes) if valid else None,overload_minutes=max(0,row['planned_minutes']-allocated) if valid and confirmed else None)
            result['rows'].append(row)
        return Response(result)
