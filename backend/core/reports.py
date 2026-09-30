"""Local weekly drafts. No provider calls, messages, or institutional approvals."""
from datetime import datetime,time,timedelta
from zoneinfo import ZoneInfo
import uuid
from django.db import connection,transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema,OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .access import scopes,READ,require
from .admin_serializers import StrictSerializer
from .time_accounting import effective
from .models import Service,Task,TaskEvent,BaselineChange,TimeEntry,Answer,QuestionnaireInstance,RoleAssignment,AuditEvent,Decision,DecisionEvent

ZONE=ZoneInfo('America/Merida')
LIMIT=1000
class ReportInput(StrictSerializer):
    start=serializers.DateField(required=False)

def bounded(query):
    rows=list(query[:LIMIT+1])
    if len(rows)>LIMIT:raise serializers.ValidationError('El informe excede el límite de 1000 registros por sección; no se genera una exportación parcial.')
    return rows

def metric(n,d):
    return {'numerator':n,'denominator':d,'pending':d-n,'label':f'{n} de {d}' if d else 'Sin alcance definido'}

@transaction.atomic
def snapshot(user,service_id,start,now):
    # First statement in this transaction: all data belong to the same DB snapshot.
    with connection.cursor() as cursor:
        cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        cursor.execute("SET LOCAL statement_timeout = '5000ms'")
    service=get_object_or_404(Service,pk=service_id,pk__in=scopes(user,READ))
    end=start+timedelta(days=7)
    lower=datetime.combine(start,time.min,ZONE)
    upper=min(datetime.combine(end,time.min,ZONE),now)
    tasks=bounded(Task.objects.filter(service=service).order_by('id').values('id','etag','title','state','committed','due','priority','blocked_since','estimated_minutes'))
    committed=[t for t in tasks if t['committed']]
    active=[t for t in committed if t['state'] not in ['accepted','cancelled']]
    questions=bounded(QuestionnaireInstance.objects.filter(service=service).order_by('id').values('id','published'))
    answers=bounded(Answer.objects.filter(instance__service=service).order_by('id').values('id','instance_id','version','etag','state'))
    events=bounded(TaskEvent.objects.filter(task__service=service,created_at__gte=lower,created_at__lt=datetime.combine(end,time.min,ZONE),created_at__lte=now).order_by('created_at','id').values('id','task_id','kind','created_at'))
    decisions=bounded(BaselineChange.objects.filter(task__service=service,reviewed_at__gte=lower,reviewed_at__lt=datetime.combine(end,time.min,ZONE),reviewed_at__lte=now).order_by('reviewed_at','id').values('id','task_id','state','reviewed_at'))
    pending=bounded(BaselineChange.objects.filter(task__service=service,state='pending').order_by('id').values('id','task_id','created_at'))
    entries=bounded(effective(TimeEntry.objects.filter(task__service=service,day__gte=start,day__lt=end,day__lte=now.astimezone(ZONE).date(),created_at__lte=now)).order_by('day','id').values('id','task_id','day','minutes','effective_minutes','correction_version','created_at'))
    operational_pending=bounded(Decision.objects.filter(service=service,state='pending').order_by('id').values('id','task_id','title','due','etag'))
    operational_events=bounded(DecisionEvent.objects.filter(service=service,created_at__gte=lower,created_at__lt=datetime.combine(end,time.min,ZONE),created_at__lte=now).order_by('created_at','id').values('id','decision_id','version','action','created_at'))
    recipients=bounded(RoleAssignment.objects.filter(service=service,role__in=READ,starts__lte=now.astimezone(ZONE).date(),ends__gte=now.astimezone(ZONE).date(),revoked_at__isnull=True,user__is_active=True).order_by('user_id').values('user_id','user__username').distinct())
    today=now.astimezone(ZONE).date()
    return {'id':str(uuid.uuid4()),'status':'draft','service':{'id':service.pk,'name':service.name},'generated_at':now,'timezone':str(ZONE),
            'period':{'start':start,'end_exclusive':end,'observed_until':upper,'partial':upper<datetime.combine(end,time.min,ZONE)},
            'current':{'observed_at':now,'accepted_tasks':metric(sum(t['state']=='accepted' for t in committed),len(committed)),
                       'cancelled_committed':sum(t['state']=='cancelled' for t in committed),'uncommitted':len(tasks)-len(committed),
                       'validated_answers':metric(sum(a['state']=='validated' for a in answers),len(questions)),
                       'published_questions':sum(q['published'] for q in questions),
                       'overdue_task_ids':[t['id'] for t in active if t['due']<today],
                       'blocked_task_ids':[t['id'] for t in active if t['state']=='blocked'],
                       'critical_task_ids':[t['id'] for t in active if t['priority']=='critical']},
            'period_activity':{'minutes':sum(e['effective_minutes'] for e in entries),'events':events,'baseline_decisions':decisions,'time_entries':entries,'decision_events':operational_events},
            'current_pending_decisions':pending,'current_pending_operational_decisions':operational_pending,'references':{'tasks':tasks,'questions':questions,'answers':answers},
            'eligible_recipients':recipients,'delivery':'not_sent',
            'limitations':['Estado actual al generar: no reconstruye el estado al cierre de una semana pasada.',
                           'Decisiones: cambios de línea base y solicitudes del registro del servicio; no todas las decisiones institucionales.',
                           'Horas por fecha de trabajo; eventos y decisiones por fecha de registro en America/Merida.',
                           'Aceptación clínica, cobertura documental y cumplimiento normativo no evaluados por este informe.',
                           'Destinatarios elegibles al generar; un envío futuro exige volver a comprobar permiso y canal aprobado.']}

class WeeklyReport(APIView):
    renderer_classes=[JSONRenderer]
    @extend_schema(parameters=[OpenApiParameter('start',OpenApiTypes.DATE,description='Inicio de un intervalo de siete días; por defecto lunes de la semana actual.')],responses=OpenApiTypes.OBJECT)
    def get(self,request,service,export=False):
        params=ReportInput(data=request.query_params);params.is_valid(raise_exception=True)
        now=timezone.now();today=now.astimezone(ZONE).date()
        start=params.validated_data.get('start',today-timedelta(days=today.weekday()))
        if start>today:raise serializers.ValidationError('El período no puede comenzar en el futuro.')
        result=snapshot(request.user,service,start,now)
        require(request.user,service,READ)
        AuditEvent.objects.create(actor=request.user,service_id=service,action='report.weekly_exported' if export else 'report.weekly_viewed',object_id=result['id'])
        response=Response(result)
        response['Cache-Control']='private, no-store'
        if export:response['Content-Disposition']=f'attachment; filename="salud-report-{service}-{start}.json"'
        return response
