from datetime import date,timedelta
from zoneinfo import ZoneInfo
from django.db import transaction
from django.db.models import Sum
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.exceptions import ValidationError,PermissionDenied
from core.models import Task,Service,Institution,TaskDependency,BaselineChange,TaskEvent,TimeEntry,WorkPlan,OutboxEvent,RoleAssignment
from core.access import require,READ,scopes
from django.shortcuts import get_object_or_404
from core.time_accounting import total
from core.coverage import coverages,covering
from core.governance import require_manage
from core.workflow import Conflict
EDIT={'manager','coordinator'}
WORK=EDIT|{'contributor','clinical','compliance'}
START=date(2026,10,1)

def today(service):return timezone.localdate(timezone=ZoneInfo(service.site.timezone))
def scoped_person(pk,service,roles=WORK):
    user=get_user_model().objects.filter(pk=pk,is_active=True).first()
    if not user:raise ValidationError('Persona no disponible.')
    require(user,service.pk,roles);return user

def fields(task):
    return {'reservation_capacity_versions':[{**r,'day':str(r['day'])} for r in task.reservations.order_by('day','person_id').values('person_id','day','capacity_version')],'reservation_plan':task.reservation_plan,'budget_bucket':task.budget_bucket,'title':task.title,'owner':task.owner_id,'starts':str(task.starts),'due':str(task.due),'priority':task.priority,'estimated_minutes':task.estimated_minutes,'acceptance_criteria':task.acceptance_criteria,'substitute':task.substitute_id,'coordinator':task.coordinator_id,'predecessors':list(task.dependencies.order_by('predecessor_id').values_list('predecessor_id',flat=True))}
def event(user,task,kind,note):TaskEvent.objects.create(task=task,actor=user,kind=kind,note=note,snapshot={**fields(task),'state':task.state,'etag':task.etag,'committed':task.committed,'actor_coverage_ids':list(coverages(task.service_id,task.owner_id).filter(user=user).values_list('id',flat=True))})

def validate_fields(service,data,task=None,user=None):
    data=dict(data)
    from core.reservations import normalize
    data['reservation_plan']=normalize(data)
    scoped_person(data['owner'],service)
    if data['substitute']:
        scoped_person(data['substitute'],service)
        if data['substitute']==data['owner']:raise ValidationError('El suplente debe ser otra persona.')
    if data['coordinator']:scoped_person(data['coordinator'],service,{'coordinator'})
    starts=date.fromisoformat(str(data['starts']));due=date.fromisoformat(str(data['due']))
    if starts<START or due<starts or (due-START).days>3660:raise ValidationError('Fechas fuera de rango: inicio mínimo 1 de octubre de 2026 e inicio no posterior al fin.')
    ids=set(data['predecessors'])
    parents=Task.objects.filter(pk__in=ids,service__site__campus__institution_id=service.site.campus.institution_id)
    if parents.count()!=len(ids):raise ValidationError('Dependencia fuera de la institución.')
    if user:
        for parent in parents:
            if parent.service_id not in scopes(user,READ):raise ValidationError('Dependencia fuera del alcance autorizado.')
    if task:
        graph={}
        for child,parent in TaskDependency.objects.filter(task__service__site__campus__institution_id=service.site.campus.institution_id).values_list('task_id','predecessor_id'):graph.setdefault(child,set()).add(parent)
        graph[task.pk]=ids
        seen=set();stack=list(ids)
        while stack:
            node=stack.pop()
            if node==task.pk:raise ValidationError('La dependencia crea un ciclo.')
            if node not in seen:seen.add(node);stack.extend(graph.get(node,[]))
    for pred in Task.objects.filter(pk__in=ids):
        if pred.state=='cancelled':raise ValidationError('No dependa de una tarea cancelada.')
        if pred.due>=starts:raise ValidationError('El inicio debe ser posterior al fin de cada predecesora.')
    if task and task.successors.filter(task__starts__lte=due).exists():raise ValidationError('El cambio invade el inicio de una sucesora; proponga primero ajustar sus fechas.')
    return data

def assign(task,data):
    for key in ['title','starts','due','priority','estimated_minutes','acceptance_criteria']:setattr(task,key,data[key])
    task.reservation_plan=data.get('reservation_plan',[]);task.budget_bucket=data.get('budget_bucket','base')
    for key in ['owner','substitute','coordinator']:setattr(task,key+'_id',data[key])
    task.etag+=1;task.save()
    TaskDependency.objects.filter(task=task).delete()
    TaskDependency.objects.bulk_create([TaskDependency(task=task,predecessor_id=pk) for pk in set(data['predecessors'])])

@transaction.atomic
def create(user,service,data):
    require(user,service.pk,EDIT)
    Institution.objects.select_for_update().get(pk=service.site.campus.institution_id)
    Service.objects.select_for_update().get(pk=service.pk)
    require(user,service.pk,EDIT)
    data=validate_fields(service,data,user=user)
    import uuid
    task=Task(service=service,deduplication_key='manual:'+str(uuid.uuid4()),state='pending')
    assign(task,data);event(user,task,'created','Propuesta de tarea, fuera de línea base.');return task

@transaction.atomic
def propose(user,pk,version,data,rationale,cancel=False):
    service=Task.objects.get(pk=pk).service
    require(user,service.pk,EDIT)
    Institution.objects.select_for_update().get(pk=service.site.campus.institution_id)
    Service.objects.select_for_update().get(pk=service.pk)
    require(user,service.pk,EDIT)
    task=Task.objects.select_for_update().get(pk=pk)
    if task.etag!=version:raise Conflict()
    if task.state=='cancelled':raise ValidationError('La tarea ya está cancelada; conserve su historial.')
    if task.baseline_changes.filter(state='pending').exists():raise ValidationError('Hay una propuesta pendiente para esta tarea.')
    data=validate_fields(service,data,task,user=user)
    proposal={**data,'starts':str(data['starts']),'due':str(data['due']),'cancel':cancel}
    change=BaselineChange.objects.create(task=task,expected_etag=task.etag,requested_by=user,proposal=proposal,previous=fields(task),rationale=rationale)
    event(user,task,'change_requested',rationale);return change

@transaction.atomic
def decide(user,pk,approve,rationale):
    original=BaselineChange.objects.select_related('task__service').get(pk=pk)
    require_manage(user,original.task.service)
    require(user,original.task.service_id,READ)
    Institution.objects.select_for_update().get(pk=original.task.service.site.campus.institution_id)
    Service.objects.select_for_update().get(pk=original.task.service_id)
    require_manage(user,original.task.service)
    require(user,original.task.service_id,READ)
    task=Task.objects.select_for_update().get(pk=original.task_id)
    change=BaselineChange.objects.select_for_update().get(pk=pk)
    if change.state!='pending':raise ValidationError('La propuesta ya fue revisada.')
    if change.requested_by_id==user.pk:raise ValidationError('Dirección debe revisar la propuesta de otra persona.')
    if approve:
        from core.reservations import check
        previous_planning=check(task.service.site.campus.institution_id)
        if task.etag!=change.expected_etag:raise Conflict()
        data=dict(change.proposal);cancel=data.pop('cancel');data=validate_fields(task.service,data,task,user=user)
        for predecessor in Task.objects.filter(pk__in=data['predecessors']).select_related('service'):
            if predecessor.service_id!=task.service_id:require_manage(user,predecessor.service)
        if cancel and task.successors.exclude(task__state='cancelled').exists():raise ValidationError('Resuelva primero las dependencias de las sucesoras.')
        task.committed=True;task.state='cancelled' if cancel else 'pending';task.blocked_since=None;task.submitted_by=None
        assign(task,data)
        invalidate_successors(user,task,change)
        from core.reservations import commit_reservations, validate_institution
        commit_reservations(task)
        validate_institution(task.service.site.campus.institution_id,previous_planning)
    change.state='approved' if approve else 'rejected';change.reviewed_by=user;change.review_reason=rationale;change.reviewed_at=timezone.now();change.save()
    event(user,task,'baseline.'+change.state,rationale);return task

@transaction.atomic
def transition(user,pk,version,target,note):
    service=Task.objects.get(pk=pk).service
    require(user,service.pk,WORK|{'director'})
    Institution.objects.select_for_update().get(pk=service.site.campus.institution_id)
    Service.objects.select_for_update().get(pk=service.pk)
    task=Task.objects.select_for_update().get(pk=pk)
    require(user,service.pk,WORK|{'director'})
    if task.etag!=version:raise Conflict()
    if not task.committed:raise ValidationError('Comprometa la tarea mediante un cambio de línea base aprobado.')
    if task.state in ['accepted','cancelled']:raise ValidationError('El cierre se conserva; proponga un cambio de línea base para reabrir.')
    if today(service)<max(START,task.starts):raise ValidationError('La actividad no ha llegado a su fecha de inicio.')
    if target=='accepted':
        require(user,service.pk,{'manager','director'})
        if task.state!='submitted' or (user.pk in {task.owner_id,task.substitute_id,task.submitted_by_id} or covering(user,service.pk,task.owner_id)):raise ValidationError('El cierre requiere revisión por otra persona.')
    elif target=='returned':
        require(user,service.pk,{'manager','director'})
        if task.state!='submitted' or (user.pk in {task.owner_id,task.substitute_id,task.submitted_by_id} or covering(user,service.pk,task.owner_id)):raise ValidationError('La devolución requiere otra persona y una entrega enviada.')
    else:
        if user.pk not in {task.owner_id,task.substitute_id} and not covering(user,service.pk,task.owner_id):require(user,service.pk,EDIT)
        if task.state=='submitted':raise ValidationError('Espere la revisión de la entrega.')
    if target in ['in_progress','submitted','accepted'] and task.dependencies.exclude(predecessor__state='accepted').exists():raise ValidationError('Hay predecesoras sin cierre aceptado.')
    if target=='submitted':task.submitted_by=user
    task.state=target;task.blocked_since=(task.blocked_since or timezone.now()) if target=='blocked' else None
    task.etag+=1;task.save();event(user,task,'state.'+target,note);return task

@transaction.atomic
def time_entry(user,task,data):
    require(user,task.service_id,WORK)
    # Match the service -> task lock order of baseline/state mutations before locking the actor.
    Service.objects.select_for_update().get(pk=task.service_id)
    task=Task.objects.select_for_update(of=('self',)).select_related('service__site').get(pk=task.pk)
    require(user,task.service_id,WORK)
    get_user_model().objects.select_for_update().get(pk=user.pk)
    if data['day']<START or data['day']>today(task.service):raise ValidationError('Registre tiempo desde el 1 de octubre de 2026 y no en el futuro.')
    old=TimeEntry.objects.filter(actor=user,client_key=data['client_key']).first()
    if old:
        if (old.task_id,old.day,old.minutes,old.note)!=(task.pk,data['day'],data['minutes'],data['note']):raise ValidationError('Clave reutilizada para otro registro.')
        return old
    if total(TimeEntry.objects.filter(actor=user,day=data['day']))+data['minutes']>1440:raise ValidationError('El tiempo diario supera 24 horas.')
    entry=TimeEntry.objects.create(task=task,actor=user,budget_bucket=task.budget_bucket,**data);event(user,task,'time.recorded',f'{entry.minutes} minutos; registro {entry.pk}.');return entry

def working_days(start,end,plan):
    if (end-start).days>3660:raise ValidationError('Intervalo de calendario excesivo.')
    holidays=set(plan.holidays)
    return sum(1 for i in range(1,max(0,(end-start).days)+1) if (start+timedelta(days=i)).weekday() in plan.weekdays and str(start+timedelta(days=i)) not in holidays)

def reminders():
    created=0
    for task_id in Task.objects.filter(committed=True).exclude(state__in=['accepted','cancelled','submitted']).values_list('pk',flat=True).iterator():
        with transaction.atomic():
            service_id=Task.objects.values_list('service_id',flat=True).get(pk=task_id)
            Service.objects.select_for_update().get(pk=service_id)
            task=Task.objects.select_for_update().select_related('service__site__campus').get(pk=task_id)
            if task.state in ['accepted','cancelled','submitted']:continue
            now=today(task.service);plan=WorkPlan.objects.filter(institution=task.service.site.campus.institution,confirmed_by__isnull=False).first()
            if not plan or now<START or now<task.due or now.weekday() not in plan.weekdays or str(now) in plan.holidays:continue
            response=task.events.filter(kind__startswith='state.').order_by('-id').first()
            anchor=max(task.due,timezone.localdate(response.created_at,timezone=ZoneInfo(task.service.site.timezone))) if response else task.due
            delay=working_days(anchor,now,plan)
            for level,recipient,minimum in [('owner',task.owner_id,0),('substitute',task.substitute_id,2),('coordinator',task.coordinator_id,3)]:
                if recipient and delay>=minimum:
                    try:scoped_person(recipient,task.service,{'coordinator'} if level=='coordinator' else WORK)
                    except (ValidationError,PermissionDenied):continue
                    _,new=OutboxEvent.objects.get_or_create(key=f'tracking:{task.pk}:{task.etag}:{level}',defaults={'task':task,'recipient_id':recipient,'task_etag':task.etag})
                    created+=int(new)
            if delay>=2:
                notified=set()
                for grant in coverages(task.service_id,task.owner_id):
                    # Explicit task substitutes already receive this level through the existing route.
                    if grant.user_id==task.substitute_id or grant.user_id in notified:continue
                    notified.add(grant.user_id)
                    _,new=OutboxEvent.objects.get_or_create(key=f'tracking:{task.pk}:{task.etag}:coverage:{grant.pk}',defaults={'task':task,'recipient_id':grant.user_id,'task_etag':task.etag,'coverage':grant})
                    created+=int(new)
    return created

def invalidate_successors(user,task,change):
    """Called while the service lock is held; retain all earlier acceptance events."""
    seen=set();pending=list(task.successors.values_list('task_id',flat=True))
    while pending:
        pk=pending.pop()
        if pk in seen:continue
        seen.add(pk)
        child=Task.objects.select_for_update().get(pk=pk)
        pending.extend(child.successors.values_list('task_id',flat=True))
        if child.state in ['accepted','submitted','in_progress']:
            child.state='returned' if child.state in ['accepted','submitted'] else 'blocked'
            child.blocked_since=timezone.now() if child.state=='blocked' else None
            child.etag+=1;child.save(update_fields=['state','blocked_since','etag'])
            event(user,child,'dependency.changed',f'Revisar por cambio aprobado en la predecesora #{task.pk}.')
            OutboxEvent.objects.get_or_create(key=f'tracking:dependency:{change.pk}:{child.pk}',defaults={'task':child,'recipient':child.owner,'task_etag':child.etag})
            notified=set()
            for grant in coverages(child.service_id,child.owner_id):
                if grant.user_id in notified:continue
                notified.add(grant.user_id)
                OutboxEvent.objects.get_or_create(key=f'tracking:dependency:{change.pk}:{child.pk}:coverage:{grant.pk}',defaults={'task':child,'recipient_id':grant.user_id,'task_etag':child.etag,'coverage':grant})

@transaction.atomic
def correct_time(user,entry_id,version,minutes,rationale):
    from core.models import TimeCorrection
    from core.time_accounting import total
    original=get_object_or_404(TimeEntry,pk=entry_id,actor=user,task__service_id__in=scopes(user,WORK))
    Service.objects.select_for_update().get(pk=original.task.service_id)
    task=Task.objects.select_for_update().get(pk=original.task_id)
    require(user,task.service_id,WORK)
    get_object_or_404(get_user_model().objects.select_for_update(),pk=user.pk,is_active=True)
    entry=TimeEntry.objects.select_for_update().get(pk=entry_id)
    latest=entry.corrections.order_by('-version').first()
    current=latest.version if latest else 0
    if version!=current:
        if latest and latest.actor_id==user.pk and current==version+1 and (latest.minutes,latest.rationale)==(minutes,rationale):return task
        raise Conflict()
    if (latest.minutes if latest else entry.minutes)==minutes:raise ValidationError('El ajuste debe cambiar los minutos efectivos.')
    if total(TimeEntry.objects.filter(actor=user,day=entry.day).exclude(pk=entry.pk))+minutes>1440:
        raise ValidationError('El tiempo diario supera 24 horas.')
    correction=TimeCorrection.objects.create(entry=entry,actor=user,version=current+1,minutes=minutes,rationale=rationale)
    event(user,task,'time.corrected',f'Registro {entry.pk}; ajuste {correction.pk}; {minutes} minutos efectivos. Motivo: {rationale}')
    return task
